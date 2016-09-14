import re
import operator
import time
import pycountry
from calendar import timegm
from copy import deepcopy
from core.cache import cache_key, cache_results
from core.db.dynamic import connection
from core.timeutils import convert_tz, display, from_timestamp, midnight_timestamp, timestamp, DATE_FMT
from datetime import datetime, timedelta
from dateutil import parser
from django.core.cache import cache
from django.conf import settings
from localization.models import Country
from pytz import timezone, utc
from metrics.models import AppleReportRecord, GoogleReportRecord
from django.db.models import Sum
from django.db.models import Q
from string import split
from bisect import bisect_left, bisect_right
from core.oauth.constants import GSUTIL_CLIENT_ID, GSUTIL_CLIENT_NOTSOSECRET, SERVICE_ACCOUNT
from core.bigquery import get_client
from core.bigquery.query_builder import render_query

_TOP_COUNTRIES_ALPHA2 = ['AU', 'BR', 'CA', 'CN', 'FR', 'DE', 'IT', 'JP', 'KR', 'LA', 'MO', 'NL',
                         'RU', 'ES', 'SE', 'SG', 'CH', 'GB', 'US', 'VN']

def google_app_sales_data(country_ids, app_str, start_date, end_date, user_id):
    all_country ='ALL'
    countryNameList = get_country_name_list()
    country_id_list = [id for id in split(str(country_ids),',')]
    if all_country in country_id_list:
        all_data = True
    else:
        all_data = False
        
    in_country =  ','.join("'{0}'".format(x) for x in country_id_list)
    
    # BigQuery project id as listed in the Google Developers Console.
    project_id = 'mobbo-dashboard'
    service_account = SERVICE_ACCOUNT
    # PKCS12 or PEM key provided by Google.
    key = settings.GOOGLE_KEY
    client = get_client(project_id, service_account=service_account, private_key_file=key, readonly=False)
    
    sql ="SELECT charged_date, buyer_country, SUM(developer_proceeds_usd) as amount \
        FROM mobbo_dashboard.google_report_records WHERE product_id= '%s' AND charged_date >= '%s' AND \
        charged_date <= '%s' AND customer_id = %d" % \
        (app_str,start_date,end_date,user_id)
        
    if not all_data:
		sql += " AND buyer_country IN (%s)" % (in_country,)
	
    sql += " GROUP BY charged_date, buyer_country"
    
    job_id, _results = client.query(sql)
    
    # Check if the query has finished running.
    complete, row_count = client.check_job(job_id)
    
    while not complete:
        complete, row_count = client.check_job(job_id)
        
    # Retrieve the results.
    results = client.get_query_rows(job_id)
    return results

def itunes_app_sales_data(country_ids, app_str, start_date, end_date, user_id):
    all_country ='ALL'
    countryNameList = get_country_name_list()
    country_id_list = [id for id in split(str(country_ids),',')]
    if all_country in country_id_list:
        all_data = True
    else:
        all_data = False
        
    in_country =  ','.join("'{0}'".format(x) for x in country_id_list)
    
    # BigQuery project id as listed in the Google Developers Console.
    project_id = 'mobbo-dashboard'
    service_account = SERVICE_ACCOUNT
    # PKCS12 or PEM key provided by Google.
    key = settings.GOOGLE_KEY
    client = get_client(project_id, service_account=service_account, private_key_file=key, readonly=False)
    
    skusql ="SELECT sku FROM mobbo_dashboard.apple_report_records  \
		WHERE apple_identifier= %s limit 1" % (app_str)
    
    job_id, _results = client.query(skusql)
    
    # Check if the query has finished running.
    complete, row_count = client.check_job(job_id)
    
    while not complete:
        complete, row_count = client.check_job(job_id)
    # Retrieve the results.
    results = client.get_query_rows(job_id)
    sku = results[0]['sku']
    
    sql ="SELECT begin_date, country_code, SUM(developer_proceeds_usd) as amount \
        FROM mobbo_dashboard.apple_report_records WHERE begin_date >= '%s' AND \
        begin_date <= '%s' AND customer_id = %d AND units > 0" % \
        (start_date,end_date,user_id)
	
    if not all_data:
        sql += " AND country_code IN (%s)" % (in_country,)
	
	if sku is not None:
		sql += " AND (apple_identifier=%s OR parent_identifier='%s')" % (app_str,sku,)
	else:
		sql += " AND apple_identifier=%s" % (app_str,)
        
    sql += " GROUP BY begin_date, country_code"
    
    job_id, _results = client.query(sql)
    
    # Check if the query has finished running.
    complete, row_count = client.check_job(job_id)
    
    while not complete:
        complete, row_count = client.check_job(job_id)
        
    # Retrieve the results.
    results = client.get_query_rows(job_id)
    
    return results

def android_app_download_data(country_ids, app_str, start_date, end_date, user_id):
    all_country ='ALL'
    countryNameList = get_country_name_list()
    country_id_list = [id for id in split(str(country_ids),',')]
    if all_country in country_id_list:
        all_data = True
    else:
        all_data = False
        
    in_country =  ','.join("'{0}'".format(x) for x in country_id_list)
    
    # BigQuery project id as listed in the Google Developers Console.
    project_id = 'mobbo-dashboard'
    service_account = SERVICE_ACCOUNT
    # PKCS12 or PEM key provided by Google.
    key = settings.GOOGLE_KEY
    client = get_client(project_id, service_account=service_account, private_key_file=key, readonly=False)
    
    sql ="SELECT date, country, SUM(daily_user_installs) as daily_user_installs \
        FROM mobbo_dashboard.google_installation_report_records  WHERE date >= '%s' AND \
        date <= '%s' AND customer_id = %d AND package_name = '%s'" % \
        (start_date,end_date,user_id,app_str)
	
    if not all_data:
        sql += " AND country IN (%s)" % (in_country,)
    sql += " GROUP BY date, country"
    
    job_id, _results = client.query(sql)
    
    # Check if the query has finished running.
    complete, row_count = client.check_job(job_id)
    
    while not complete:
        complete, row_count = client.check_job(job_id)
        
    # Retrieve the results.
    results = client.get_query_rows(job_id)
    
    return results

def itunes_app_download_data(country_ids, app_str, start_date, end_date, user_id):
    all_country ='ALL'
    countryNameList = get_country_name_list()
    country_id_list = [id for id in split(str(country_ids),',')]
    if all_country in country_id_list:
        all_data = True
    else:
        all_data = False
        
    in_country =  ','.join("'{0}'".format(x) for x in country_id_list)
    
    # BigQuery project id as listed in the Google Developers Console.
    project_id = 'mobbo-dashboard'
    service_account = SERVICE_ACCOUNT
    # PKCS12 or PEM key provided by Google.
    key = settings.GOOGLE_KEY
    client = get_client(project_id, service_account=service_account, private_key_file=key, readonly=False)
    
    sql ="SELECT begin_date, country_code, SUM(units) as units \
        FROM mobbo_dashboard.apple_report_records WHERE begin_date >= '%s' AND \
        begin_date <= '%s' AND apple_identifier = %d AND customer_id = %d AND units > 0 AND (product_type_identifier = '1F' OR product_type_identifier = '1')" % \
        (start_date,end_date,app_str,user_id)
	
    if not all_data:
        sql += " AND country_code IN (%s)" % (in_country,)
    sql += " GROUP BY begin_date, country_code"
    
    job_id, _results = client.query(sql)
    
    # Check if the query has finished running.
    complete, row_count = client.check_job(job_id)
    
    while not complete:
        complete, row_count = client.check_job(job_id)
        
    # Retrieve the results.
    results = client.get_query_rows(job_id)
    
    return results
    

def android_app_revenue_stats(records,startDate,endDate,country_ids):	
	all_country ='ALL'
	countryNameList = get_country_name_list()
	country_id_list = [id for id in split(str(country_ids),',')]
	all_data = True if all_country in country_id_list else False
	
	_json = {}
	days_array = get_days_array(startDate,endDate)
	for record in records:
		country = str(record['buyer_country'])
		
		if not all_data:
			if country_id_list and not country in country_id_list:
				continue
		country_code = record['buyer_country'] if record['buyer_country'] else 'Unknown'
		countryName = countryCode2Name(country_code)
		date = datetime.fromtimestamp(int(record['charged_date']))
		revenue_time = str(date)
		revenue = round(record['amount'],2)
		if not _json.has_key(countryName):
			_json[countryName] = {
				'key': countryName,
				'country_code' : country_code,
				'values': [ [i,0] for i in days_array ],
				'total': 0,
			}
		
		chart_time = gp_date2millis(revenue_time)
		index = days_array.index(chart_time)
		_json[countryName]['values'][index][1] = revenue
		_json[countryName]['total'] += revenue
	
	sorted_data = sorted([{'total': round(_json[x]['total'],2),'country':_json[x]['country_code'],'name':_json[x]['key'],
								'revenue_series':_json[x]['values']} for x in _json],key=operator.itemgetter('total'),reverse=True)	
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
		finalResults['Other'] = {'total':0,'country':'Other','name':'Other','revenue_series':[ [i,0] for i in days_array ]}
	
	for data in sorted_data:
		if count < 6:
			finalResults[data['country']] = {
				'total': data['total'],
				'country' : data['country'],
				'revenue_series' : data['revenue_series'],
				'name' : data['name']
			}
		else:
			countrytotal = int(countrytotal + data['total'])
			finalResults['Other']['total'] = countrytotal
			for i, j in enumerate(data['revenue_series']):
				otherData = int(finalResults['Other']['revenue_series'][i][1])
				dateData = int(j[1])
				totalByDate = otherData + dateData
				finalResults['Other']['revenue_series'][i][1] = totalByDate
		
		count +=1
	
	chartData = sorted([{'total': finalResults[x]['total'],'key':finalResults[x]['name'],'name':finalResults[x]['name'],
								'values':finalResults[x]['revenue_series']} for x in finalResults],key=operator.itemgetter('total'),reverse=True)
	info = {
		'chartData':chartData, 
		'results':sorted_data, 
		'total':total,
		'sortedData' : sortedData
	}

	return info


def itunes_app_revenue_stats(records,startDate,endDate,country_ids):
	
	all_country ='ALL'
	countryNameList = get_country_name_list()
	country_id_list = [id for id in split(str(country_ids),',')]
	all_data = True if all_country in country_id_list else False
	
	_json = {}
	days_array = get_days_array(startDate,endDate)
	for record in records:
		country = str(record['country_code'])
		
		if not all_data:
			if country_id_list and not country in country_id_list:
				continue
		country_code = record['country_code'] if record['country_code'] else 'Unknown'
		countryName = countryCode2Name(country_code)
		date = datetime.fromtimestamp(int(record['begin_date']))
		revenue_time = str(date)
		revenue = round(record['amount'],2)
		if not _json.has_key(countryName):
			_json[countryName] = {
				'key': countryName,
				'country_code' : country_code,
				'values': [ [i,0] for i in days_array ],
				'total': 0,
			}
		
		chart_time = gp_date2millis(revenue_time)
		index = days_array.index(chart_time)
		_json[countryName]['values'][index][1] = revenue
		_json[countryName]['total'] += revenue
	
	sorted_data = sorted([{'total': round(_json[x]['total'],2),'country':_json[x]['country_code'],'name':_json[x]['key'],
								'revenue_series':_json[x]['values']} for x in _json],key=operator.itemgetter('total'),reverse=True)	
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
		finalResults['Other'] = {'total':0,'country':'Other','name':'Other','revenue_series':[ [i,0] for i in days_array ]}
	
	for data in sorted_data:
		if count < 6:
			finalResults[data['country']] = {
				'total': data['total'],
				'country' : data['country'],
				'revenue_series' : data['revenue_series'],
				'name' : data['name']
			}
		else:
			countrytotal = int(countrytotal + data['total'])
			finalResults['Other']['total'] = countrytotal
			for i, j in enumerate(data['revenue_series']):
				otherData = int(finalResults['Other']['revenue_series'][i][1])
				dateData = int(j[1])
				totalByDate = otherData + dateData
				finalResults['Other']['revenue_series'][i][1] = totalByDate
		
		count +=1
	
	chartData = sorted([{'total': finalResults[x]['total'],'key':finalResults[x]['name'],'name':finalResults[x]['name'],
								'values':finalResults[x]['revenue_series']} for x in finalResults],key=operator.itemgetter('total'),reverse=True)
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
		country = str(record['country'])
		
		if not all_data:
			if country_id_list and not country in country_id_list:
				continue
		country_code = record['country'] if record['country'] else 'Unknown'
		countryName = countryCode2Name(country_code)
		date = datetime.fromtimestamp(int(record['date']))
		download_time = str(date)
		download = int(record['daily_user_installs'])
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
	
	chartData = sorted([{'total': finalResults[x]['total'],'key':finalResults[x]['name'],'name':finalResults[x]['name'],
								'values':finalResults[x]['downloads_series']} for x in finalResults],key=operator.itemgetter('total'),reverse=True)
	info = {
		'chartData':chartData, 
		'results':sorted_data, 
		'total':total,
		'sortedData' : sortedData
	}
	
	return info
	
def itunes_app_download_stats(records,startDate,endDate,country_ids):
	
	all_country ='ALL'
	countryNameList = get_country_name_list()
	country_id_list = [id for id in split(str(country_ids),',')]
	all_data = True if all_country in country_id_list else False
	
	_json = {}
	days_array = get_days_array(startDate,endDate)
	for record in records:
		country = str(record['country_code'])
		
		if not all_data:
			if country_id_list and not country in country_id_list:
				continue
		country_code = record['country_code'] if record['country_code'] else 'Unknown'
		countryName = countryCode2Name(country_code)
		date = datetime.fromtimestamp(int(record['begin_date']))
		download_time = str(date)
		download = int(record['units'])
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
	
	sorted_data = sorted([{'total': round(_json[x]['total'],2),'country':_json[x]['country_code'],'name':_json[x]['key'],
								'download_series':_json[x]['values']} for x in _json],key=operator.itemgetter('total'),reverse=True)	
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
		finalResults['Other'] = {'total':0,'country':'Other','name':'Other','download_series':[ [i,0] for i in days_array ]}
	
	for data in sorted_data:
		if count < 6:
			finalResults[data['country']] = {
				'total': data['total'],
				'country' : data['country'],
				'download_series' : data['download_series'],
				'name' : data['name']
			}
		else:
			countrytotal = int(countrytotal + data['total'])
			finalResults['Other']['total'] = countrytotal
			for i, j in enumerate(data['download_series']):
				otherData = int(finalResults['Other']['download_series'][i][1])
				dateData = int(j[1])
				totalByDate = otherData + dateData
				finalResults['Other']['download_series'][i][1] = totalByDate
		
		count +=1
	
	chartData = sorted([{'total': finalResults[x]['total'],'key':finalResults[x]['name'],'name':finalResults[x]['name'],
								'values':finalResults[x]['download_series']} for x in finalResults],key=operator.itemgetter('total'),reverse=True)
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
