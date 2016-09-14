import re
import operator
from calendar import timegm
from copy import deepcopy
from core.cache import cache_key, cache_results
from core.db.dynamic import connection
from core.timeutils import convert_tz, display, from_timestamp, midnight_timestamp, timestamp, DATE_FMT
from datetime import datetime, timedelta
import time
from dateutil import parser
from django.core.cache import cache
from localization.models import Country
from pytz import timezone, utc
from metrics.models import AppleReportRecord, GoogleReportRecord
from django.db.models import Sum
from django.db.models import Q
from string import split
import pycountry
from bisect import bisect_left, bisect_right

_TOP_COUNTRIES_ALPHA2 = ['AU', 'BR', 'CA', 'CN', 'FR', 'DE', 'IT', 'JP', 'KR', 'LA', 'MO', 'NL',
                         'RU', 'ES', 'SE', 'SG', 'CH', 'GB', 'US', 'VN']

_ALL_COUNTRY_SALES_DATA = """
  SELECT
    charged_date,
    charged_time,
    product_id,
    buyer_country,
    sum(amount_merchant_currency) as amount_merchant_currency,
    sale_currency
  FROM
    google_report_records
  WHERE
    product_id= %s AND charged_date >= %s AND charged_date <= %s AND customer_id = %s
  GROUP BY
    charged_date, buyer_country
  ORDER BY
    sum(amount_merchant_currency)	
  ;
  """

_COUNTRY_SALES_DATA = """
  SELECT 
    charged_date, 
    charged_time, 
    product_id, 
    buyer_country,
    sum(amount_merchant_currency) as amount_merchant_currency,
    sale_currency
  FROM 
    google_report_records 
  WHERE product_id = %s AND charged_date >= %s
    AND charged_date <= %s AND buyer_country IN %s AND customer_id = %s GROUP BY charged_date, buyer_country ORDER BY charged_date ASC ;
  """


def all_country_sales_data(app_id, platform_type_id, start_date, end_date, user_id, countries_alpha2, all_country):
	if platform_type_id == 2:
		revenue_data = android_all_country_sales_data(app_id, start_date, end_date, user_id, countries_alpha2, all_country)
	else:
		revenue_data = itunes_all_country_sales_data(app_id, start_date, end_date, user_id, countries_alpha2, all_country)
	
	return revenue_data
	
		
def android_all_country_sales_data(app_id, start_date, end_date, user_id, countries_alpha2, all_country):
	
	tempResults = {}
	records = GoogleReportRecord.objects.all()\
				.filter(charged_date__gte=start_date)\
				.filter(charged_date__lte=end_date)\
				.filter(product_id=app_id)\
				.filter(customer_id=user_id)\
				.filter(developer_proceeds_usd__gt=0)\
				.exclude(financial_status='Refund')\
				.values('charged_date','buyer_country')\
				.annotate(amount=Sum('developer_proceeds_usd'))\
				.values('charged_date','buyer_country','amount','buyer_country__display_name')\
				.order_by('charged_date')
				
	if all_country is False:
		records = records.filter(buyer_country__in=countries_alpha2)
		
	for row in records:
		buyer_country, country_name = row['buyer_country'], row['buyer_country__display_name']
		tempResults[buyer_country] = {
			'revenue': {}, 'revenue_series': [],
			'total_revenue': [],
			'name': country_name,
		}
	
	for row in records:
		date, country, amount, country_name = row['charged_date'], str(row['buyer_country']), row['amount'], row['buyer_country__display_name']
		tempResults[country]['revenue'][date] = round(amount,2)
	
	daysInAnalysisPeriod = (end_date - start_date + timedelta(days=1)).days
	for delta in range(daysInAnalysisPeriod):
		date = start_date + timedelta(days=delta)
		for country in tempResults:
			tempResults[country]['revenue_series'].append(tempResults[country].get('revenue', {}).get(date, 0))
	
	for country in tempResults:
		tempResults[country]['total_revenue'] = sum(tempResults[country]['revenue_series'])
	
	sorted_data = sorted([{'total': tempResults[x]['total_revenue'],'country':x,'name':tempResults[x]['name'],
								'revenue_series':tempResults[x]['revenue_series']} for x in tempResults],key=operator.itemgetter('total'),reverse=True)
	
	
	sortedData = {}
	for data in sorted_data:
		country = data['country']
		sortedData[country] = data['total']
		
		
	country_length = len(sorted_data)
	
	finalResults = {}
	count=0
	if country_length < 6:
		for data in sorted_data:
			finalResults[data['country']] = {
				'revenue': data['total'],
				'country_code' : data['country'],
				'revenue_data' : data['revenue_series'],
				'name' : data['name']
			}
	else:
		finalResults['Other'] = {
			'revenue': 0,
			'country_code' : 'Other',
			'revenue_data' : [],
			'name' : 'Other'
		}
		for delta in range(daysInAnalysisPeriod):
			finalResults['Other']['revenue_data'].append(0)
		for data in sorted_data:
			if count < 6:
				finalResults[data['country']] = {
					'revenue': data['total'],
					'country_code' : data['country'],
					'revenue_data' : data['revenue_series'],
					'name' : data['name']
				}
			else:
				for i, j in enumerate(data['revenue_series']):
					otherData = float(finalResults['Other']['revenue_data'][i])
					dateData = float(j)
					totalByDate = otherData + dateData
					finalResults['Other']['revenue_data'][i] = totalByDate
						
			count +=1
	
	
	sorted_data_final = sorted([{'total': finalResults[x]['revenue'],'country':x,
							'revenue_series':finalResults[x]['revenue_data']} for x in finalResults],key=operator.itemgetter('total'),reverse=True)
	
	chartData = []
	for j, countryData in enumerate(sorted_data_final):
		country = sorted_data_final[j]['country']
		name = finalResults[country]['name']
		country_code = finalResults[country]['country_code']
		chartData.append({'key':name,'country_code':country_code,'values':[]})
	
	total = 0
	for i, countryData in enumerate(sorted_data_final):
		total += countryData['total']
		for j, delta in enumerate(range(daysInAnalysisPeriod)):
			date = start_date + timedelta(days=delta)
			revenue = sorted_data_final[i]['revenue_series'][j]
			revenueDate = date.strftime(DATE_FMT)
			timestamp = int(datetime.strptime(revenueDate, "%Y-%m-%d").strftime('%s')) * 1000
			
			chartData[i]['values'].append([timestamp,revenue])
	
	
	info = {
		'chartData':chartData, 
		'results':sorted_data, 
		'total':total,
		'sortedData' : sortedData
	}
	
	return info

def itunes_all_country_sales_data(app_identifier, start_date, end_date, user_id, countries_alpha2, all_country):
	
	appleReportObject = AppleReportRecord.objects.filter(apple_identifier=app_identifier).values('sku').first()
	sku = appleReportObject['sku']
	
	tempResults = {}
	records = AppleReportRecord.objects.all()\
				.filter(begin_date__gte=start_date)\
				.filter(begin_date__lte=end_date)\
				.filter(units__gte=0)\
				.filter(customer_id=user_id)\
				.filter(developer_proceeds_usd__gt=0)\
				.values('begin_date','country_code')\
				.annotate(amount=Sum('developer_proceeds_usd'))\
				.values('begin_date','country_code','amount','country_code__display_name')\
				.order_by('begin_date')
	
	if sku is not None:
		records = records.filter(Q(apple_identifier=app_identifier) | Q(parent_identifier=sku))
	else:
		records = records.filter(apple_identifier=app_identifier)
	
	if all_country is False:
		records = records.filter(country_code__in=countries_alpha2)
		
	for row in records:
		buyer_country, country_name = row['country_code'], row['country_code__display_name']
		tempResults[buyer_country] = {
			'revenue': {}, 'revenue_series': [],
			'total_revenue': [],
			'name': country_name,
		}
	
	for row in records:
		date, country, amount = row['begin_date'], str(row['country_code']), row['amount']
		tempResults[country]['revenue'][date] = round(amount,2)
	
	daysInAnalysisPeriod = (end_date - start_date + timedelta(days=1)).days
	for delta in range(daysInAnalysisPeriod):
		date = start_date + timedelta(days=delta)
		for country in tempResults:
			tempResults[country]['revenue_series'].append(tempResults[country].get('revenue', {}).get(date, 0))
	
	for country in tempResults:
		tempResults[country]['total_revenue'] = sum(tempResults[country]['revenue_series'])
	
	sorted_data = sorted([{'total': tempResults[x]['total_revenue'],'country':x,'name':tempResults[x]['name'],
								'revenue_series':tempResults[x]['revenue_series']} for x in tempResults],key=operator.itemgetter('total'),reverse=True)
	
	
	sortedData = {}
	for data in sorted_data:
		country = data['country']
		sortedData[country] = data['total']
		
		
	country_length = len(sorted_data)
	
	finalResults = {}
	count=0
	if country_length < 6:
		for data in sorted_data:
			finalResults[data['country']] = {
				'revenue': data['total'],
				'country_code' : data['country'],
				'revenue_data' : data['revenue_series'],
				'name' : data['name']
			}
	else:
		finalResults['Other'] = {
			'revenue': 0,
			'country_code' : 'Other',
			'revenue_data' : [],
			'name' : 'Other'
		}
		for delta in range(daysInAnalysisPeriod):
			finalResults['Other']['revenue_data'].append(0)
		for data in sorted_data:
			if count < 6:
				finalResults[data['country']] = {
					'revenue': data['total'],
					'country_code' : data['country'],
					'revenue_data' : data['revenue_series'],
					'name' : data['name']
				}
			else:
				for i, j in enumerate(data['revenue_series']):
					otherData = float(finalResults['Other']['revenue_data'][i])
					dateData = float(j)
					totalByDate = otherData + dateData
					finalResults['Other']['revenue_data'][i] = totalByDate
						
			count +=1
	
	
	sorted_data_final = sorted([{'total': finalResults[x]['revenue'],'country':x,
							'revenue_series':finalResults[x]['revenue_data']} for x in finalResults],key=operator.itemgetter('total'),reverse=True)
	
	chartData = []
	for j, countryData in enumerate(sorted_data_final):
		country = sorted_data_final[j]['country']
		name = finalResults[country]['name']
		country_code = finalResults[country]['country_code']
		chartData.append({'key':name,'country_code':country_code,'values':[]})
	
	total = 0
	for i, countryData in enumerate(sorted_data_final):
		total += countryData['total']
		for j, delta in enumerate(range(daysInAnalysisPeriod)):
			date = start_date + timedelta(days=delta)
			revenue = sorted_data_final[i]['revenue_series'][j]
			revenueDate = date.strftime(DATE_FMT)
			timestamp = int(datetime.strptime(revenueDate, "%Y-%m-%d").strftime('%s')) * 1000
			
			chartData[i]['values'].append([timestamp,revenue])
	
	
	info = {
		'chartData':chartData, 
		'results':sorted_data, 
		'total':total,
		'sortedData' : sortedData
	}
	return info

def top_countries():
  countries = Country.objects.filter(alpha2__in=_TOP_COUNTRIES_ALPHA2)
  ret = []
  ret.append({'id': 'ALL', 'name': 'All Countries'})
  for country in countries:
    ret.append({'id': country.alpha2, 'name': country.display_name})

  ret = sorted(ret, key=lambda x: x['name'])
  return ret


def all_countries():
	countries = Country.objects.all()
	ret = []
	ret.append({'id': 'ALL', 'name': 'All Countries', 'top': True})
	for country in countries:
		if country.alpha2 in _TOP_COUNTRIES_ALPHA2:
			top = True
		else:
			top = False
		name = country.display_name.encode('utf8')	
		ret.append({'id': country.alpha2, 'name': name,'top': top})
	ret = sorted(ret, key=lambda x: x['name'])
	return ret

def get_country_name(alpha2_code):
	country = Country.objects.filter(alpha2=alpha2_code).first()
	countryName = country.display_name.encode('utf-8')
	return str(countryName)

def get_country_name_list():
	countries = Country.objects.all()
	tempResults = {}
	for country in countries:
		tempResults[country.alpha2] = {'name':{}}
		tempResults[country.alpha2]['name'][country.alpha2] = country.name
	
	return tempResults

def all_country_download_stats(app_identifier, platform_type_id, start_date, end_date, user_id, countries_alpha2, all_country):

	appleReportObject = AppleReportRecord.objects.filter(apple_identifier=app_identifier).values('sku').first()
	sku = appleReportObject['sku']
	
	tempResults = {}
	records = AppleReportRecord.objects.all()\
				.filter(begin_date__gte=start_date)\
				.filter(begin_date__lte=end_date)\
				.filter(apple_identifier=app_identifier)\
				.filter(units__gt=0)\
				.filter(customer_id=user_id)\
				.filter(Q(product_type_identifier='1F') | Q(product_type_identifier=1))\
				.values('begin_date','country_code')\
				.annotate(units=Sum('units'))\
				.values('begin_date','country_code','units','country_code__display_name')\
				.order_by('begin_date')
				
	if all_country is False:
		records = records.filter(country_code__in=countries_alpha2)
		

	for row in records:
		buyer_country, country_name = row['country_code'], row['country_code__display_name']
		tempResults[buyer_country] = {
			'downloads': {}, 'downloads_series': [],
			'total_downloads': [],
			'name': country_name,
		}
	
	for row in records:
		date, country, amount = row['begin_date'], str(row['country_code']), row['units']
		tempResults[country]['downloads'][date] = int(amount)
	
	daysInAnalysisPeriod = (end_date - start_date + timedelta(days=1)).days
	for delta in range(daysInAnalysisPeriod):
		date = start_date + timedelta(days=delta)
		for country in tempResults:
			tempResults[country]['downloads_series'].append(tempResults[country].get('downloads', {}).get(date, 0))
	
	for country in tempResults:
		tempResults[country]['total_downloads'] = sum(tempResults[country]['downloads_series'])
	
	sorted_data = sorted([{'total': tempResults[x]['total_downloads'],'country':x,'name':tempResults[x]['name'],
								'downloads_series':tempResults[x]['downloads_series']} for x in tempResults],key=operator.itemgetter('total'),reverse=True)
	
	
	sortedData = {}
	for data in sorted_data:
		country = data['country']
		sortedData[country] = data['total']
		
		
	country_length = len(sorted_data)
	
	finalResults = {}
	count=0
	if country_length < 6:
		for data in sorted_data:
			finalResults[data['country']] = {
				'download': data['total'],
				'country_code' : data['country'],
				'download_data' : data['downloads_series'],
				'name' : data['name']
			}
	else:
		finalResults['Other'] = {
			'download': 0,
			'country_code' : 'Other',
			'download_data' : [],
			'name' : 'Other'
		}
		for delta in range(daysInAnalysisPeriod):
			finalResults['Other']['download_data'].append(0)
		for data in sorted_data:
			if count < 6:
				finalResults[data['country']] = {
					'download': data['total'],
					'country_code' : data['country'],
					'download_data' : data['downloads_series'],
					'name' : data['name']
				}
			else:
				for i, j in enumerate(data['downloads_series']):
					otherData = int(finalResults['Other']['download_data'][i])
					dateData = int(j)
					totalByDate = otherData + dateData
					finalResults['Other']['download_data'][i] = totalByDate
						
			count +=1
	
	
	sorted_data_final = sorted([{'total': finalResults[x]['download'],'country':x,
							'downloads_series':finalResults[x]['download_data']} for x in finalResults],key=operator.itemgetter('total'),reverse=True)
	
	chartData = []
	for j, countryData in enumerate(sorted_data_final):
		country = sorted_data_final[j]['country']
		name = finalResults[country]['name']
		country_code = finalResults[country]['country_code']
		chartData.append({'key':name,'country_code':country_code,'values':[]})
	
	total = 0
	for i, countryData in enumerate(sorted_data_final):
		total += countryData['total']
		for j, delta in enumerate(range(daysInAnalysisPeriod)):
			date = start_date + timedelta(days=delta)
			revenue = sorted_data_final[i]['downloads_series'][j]
			revenueDate = date.strftime(DATE_FMT)
			timestamp = int(datetime.strptime(revenueDate, "%Y-%m-%d").strftime('%s')) * 1000
			
			chartData[i]['values'].append([timestamp,revenue])
	
	
	info = {
		'chartData':chartData, 
		'results':sorted_data, 
		'total':total,
		'sortedData' : sortedData
	}
	
	return info


def android_app_download_stats(records,startDate,endDate,country_ids):
	
	all_country ='ALL'
	countryNameList = get_country_name_list()
	country_id_list = [id for id in split(str(country_ids),',')]
	all_data = True if all_country in country_id_list else False
	
	_json = {}
	days_array = get_days_array(startDate,endDate)
	for record in records:
		country = str(record.country)
		
		if not all_data:
			if country_id_list and not country in country_id_list:
				continue
		country_code = record.country if record.country else 'Unknown'
		countryName = countryCode2Name(country_code)
		download_time = str(record.date)
		download = int(record.daily_user_installs)
		if not _json.has_key(countryName):
			_json[countryName] = {
				'key': countryName,
				'country_code' : country_code,
				'values': [ [i,0] for i in days_array ],
				'total': 0,
			}
		
		chart_time = gp_date2millis(download_time)
		index = days_array.index(chart_time)
		_json[countryName]['values'][index][1] = download
		_json[countryName]['total'] += download
		
	
	sorted_data = sorted([{'total': _json[x]['total'],'country':_json[x]['country_code'],'name':_json[x]['key'],
								'downloads_series':_json[x]['values']} for x in _json],key=operator.itemgetter('total'),reverse=True)	
		
	sortedData = {}
	for data in sorted_data:
		country = data['country']
		sortedData[country] = data['total']
		
	total = sum(item['total'] for item in sorted_data)
	
	country_length = len(sorted_data)
	count=0
	countrytotal = 0
	finalResults = {}
	if country_length > 6:
		finalResults['Other'] = {'total':0,'country':'Other','name':'Other','downloads_series':[ [i,0] for i in days_array ]}
	
	for data in sorted_data:
		if count < 6:
			finalResults[data['country']] = {
				'total': data['total'],
				'country' : data['country'],
				'downloads_series' : data['downloads_series'],
				'name' : data['name']
			}
		else:
			countrytotal = int(countrytotal + data['total'])
			finalResults['Other']['total'] = countrytotal
			for i, j in enumerate(data['downloads_series']):
				otherData = int(finalResults['Other']['downloads_series'][i][1])
				dateData = int(j[1])
				totalByDate = otherData + dateData
				finalResults['Other']['downloads_series'][i][1] = totalByDate
		
		count +=1
	
	chartData = sorted([{'total': finalResults[x]['total'],'key':finalResults[x]['country'],'name':finalResults[x]['name'],
								'values':finalResults[x]['downloads_series']} for x in finalResults],key=operator.itemgetter('total'),reverse=True)
	info = {
		'chartData':chartData, 
		'results':sorted_data, 
		'total':total,
		'sortedData' : sortedData
	}
	
	return info


def countryCode2Name(countryCode):
	try:
		name = pycountry.countries.get(alpha2=countryCode).name
		return str(name)
	except:
		#print countryCode
		return countryCode	

def gp_date2millis(gp_time):
	gp_time = gp_time[:10]
        tt = datetime.strptime(gp_time, "%Y-%m-%d")
        t = time.mktime(tt.timetuple())
        return int(t*1000)


def get_days_array(startDate,endDate):
	arr = []
	daysInAnalysisPeriod = (endDate - startDate + timedelta(days=1)).days
	for delta in range(daysInAnalysisPeriod):
		gpdate = startDate + timedelta(days=delta)
		timestamp = gp_date2millis(str(gpdate))
		arr.append(timestamp)
	return arr

def round_timestamp(ts):
	dt = datetime.fromtimestamp(float(ts))
	d_truncated = date(dt.year, dt.month, dt.day)
	ts_rounded  = time.mktime(d_truncated.timetuple())
	return int(ts_rounded)
