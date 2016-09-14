from oauth2client import client
import os 
import json
import httplib2
import traceback, sys
from bisect import bisect_left, bisect_right
from mobbo.settings.common import HOSTNAME
from dashboard import rankutils
from appinfo.models import AppInfo
import requests, urllib
import datetime, time

#######################################
supported_app_stores = {
    'itunes': {
        'fields' : [
        {'disp':'Display Name',
            'name':'display_name',
            'type':'text',
        },
        {'disp':'User Id',
            'name':'user_id',
            'type':'text',
        },
        {'disp':'User Signature',
            'name':'user_sig',
            'type':'password',
        },
        ],
        'submit': ['', 'Add Account'],
        'message': 'chratboost message',
        'label': 'iTunes Connect',
        'icon': 'app-store.jpeg',
    },
    'googleplay': {
        'fields' : [
        {'disp':'Display Name',
            'name':'display_name',
            'type':'text',
        },
        {'disp':'User Id',
            'name':'user_id',
            'type':'text',
        },
        {'disp':'User Signature',
            'name':'user_sig',
            'type':'password',
        },
        ],
        'submit': ['', 'Add Account'],
        'message': 'chratboost message',
        'label': 'Google Play',
        'icon': 'google-play.png',
    },
}
supported_platforms = {
	'admob': {
		'fields' : [],
		'submit': ['ad-mob.png','Connect with Google'],
		'message': 'By adding your account, you acknowledge that you have read and agree to the Analytics Terms of the service.',
	},
        'adx': {
                'fields' : [],
                'submit': ['adx.png','Connect with Google'],
                'message': 'By adding your account, you acknowledge that you have read and agree to the Analytics Terms of the service.',
        },
	'chartboost': {
                'fields' : [
				{'disp':'Display Name',
			 	 'name':'display_name',
			 	 'type':'text',
				},
				{'disp':'User Id',
				 'name':'user_id',
				 'type':'text',
				},
				{'disp':'User Signature',
				 'name':'user_sig',
				 'type':'password',
				},
			    ],
                'submit': ['chartboost.png', 'Connect Account'],
                'message': 'By adding your account, you acknowledge that you have read and agree to the Analytics Terms of the service.',
        },
	'facebook': {
                'fields' : [],
                'submit' : ['facebook.png', 'Connect with Facebook'],
                'message': 'By adding your account, you acknowledge that you have read and agree to the Analytics Terms of the service.',
        },
        'vungle': {
                'fields' : [
                                {'disp':'Display Name',
                                 'name':'display_name',
                                 'type':'text',
                                },
                                {'disp':'Reporting Api Key',
                                 'name':'api_key',
                                 'type':'text',
                                },
                            ],
                'submit': ['vungle.png', 'Connect Account'],
                'message': 'By adding your account, you acknowledge that you have read and agree to the Analytics Terms of the service.',
        },
        'adcolony': {
                'fields' : [
                                {'disp':'Display Name',
                                 'name':'display_name',
                                 'type':'text',
                                },
                                {'disp':'Reporting Api Key',
                                 'name':'api_key',
                                 'type':'text',
                                },
                            ],
                'submit': ['adcolony.png', 'Connect Account'],
                'message': 'By adding your account, you acknowledge that you have read and agree to the Analytics Terms of the service.',
        },
        #####
        # Too Buggy for production
        #####
        #'inmobi': {
                #'fields' : [
                                #{'disp':'Email',
                                 #'name':'email',
                                 #'type':'text',
                                #},
                                #{'disp':'Password',
                                 #'name':'password',
                                 #'type':'password',
                                #},
                                #{'disp':'Api Key',
                                 #'name':'api_key',
                                 #'type':'text',
                                #},
                            #],
                #'submit': ['inmobi.jpg', 'Connect Account'],
                #'message': 'By adding your account, you acknowledge that you have read and agree to the Analytics Terms of the service.',
        #},
        #######
        # Will Be Added When data is stored in DB
        # TOCHECK: Doesn't support reporting by country (?)
        #'tapjoy': {
                #'fields' : [
                                #{'disp':'Email',
                                 #'name':'email',
                                 #'type':'text',
                                #},
                                #{'disp':'Ad Reporting API Key',
                                 #'name':'api_key',
                                 #'type':'text',
                                #},
                            #],
                #'submit': ['tapjoy.png', 'Connect Account'],
                #'message': 'By adding your account, you acknowledge that you have read and agree to the Analytics Terms of the service.',
        #},
        ######################
	#'adtech': {
		#'action' : '/ad-revenues/adtech/signup',
		#'fields' : [
				#{'disp': 'IQ Login Name',
				 #'name': 'login_name',
				 #'type': 'text',
				#},
				#{'disp':'IQ Login Password',
                                 #'name':'login_password',
                                 #'type':'password',
                                #},
			   #],
		#'submit' : ['', 'Add Account'],
		#'message': 'adtech message',
	#},
} 



###############
# period handeling:
###############


#def get_x_months_back(x):
    #today = datetime.datetime.today()
    #x_months = datetime.timedelta(days=x*30)
    #t = today - x_months
    #return t.strftime('%Y-%m-%d')
    
#def get_today():
    #today = datetime.datetime.today()
    #return today.strftime('%Y-%m-%d')

#epoch = datetime.datetime.utcfromtimestamp(0)

#def unix_time_millis(dt):
    #return (dt - epoch).total_seconds() #* 1000.0
    
#def get_today_unix():
    #dt = datetime.datetime.today()
    #return unix_time_millis(dt)
    
#def get_x_months_back_unix(x):
    #today = datetime.datetime.today()
    #x_months = datetime.timedelta(days=x*30)
    #dt = today - x_months
    #return unix_time_millis(dt)
     


def calc_revenue_percentage(curr, prev):
	try:
		return 100 - round((float(curr)/float(prev))*100)
	except:
		return json.dumps(float('nan'))



def getColor(rev_percentage):
	if rev_percentage > 0:
		return 'green'
	elif rev_percentage < 0:
		return 'red'
	else:
		return 'grey'

import pycountry
def countryCode2Name(countryCode):
	try:
		name = pycountry.countries.get(alpha2=countryCode).name
		return str(name)
	except:
		#print countryCode
		return countryCode


######################
######  adtech  ######
######################
#adtech_urls = {
	#'login'  : 'https://api-doc.adtech.de/logintoken.jsp',
	#'reports': '',
	#}
#def adtec_validate(username, password):
	#params = {
		#'username': username,
		#'password': password,
	#}
	#response = requests.post(adtech_urls['login'], params=params)
	#token = adtech_parseToken(response)
	#return token

#def adtech_parseToken(response):
	#token = str(response.text).replace('\n','').replace(' ','')
	#if token == "loginfailed:errorcode404":
		#return None
	#return token

#def adtech_pull_reports(user):
	#url = adtech_urls['reports']
	#return None


##################################################

def get_chartData(user, platform, appId, breakdownBy, countries, since, until):
	try:
            service = get_service_by_platform(platform)
            if service:
                return service.produce_chart_json(user,appId,breakdownBy,countries,since,until)
            else:
                return []
	except:	
		traceback.print_exc(file=sys.stdout)
		raise Exception()


DAY_SECONDS = 86400
def get_days_array_len(s,u):
	since = int(round_timestamp(s))
	until = int(round_timestamp(u))
	return (until - since)/DAY_SECONDS

DAY_MILLIS = 86400000
def get_days_array(s,u):
	since = int(round_timestamp(s)*1000)
	until = int(round_timestamp(u)*1000) #+ DAY_MILLIS
	arr = []
	temp = since
	while temp <= until:
		arr.append(temp)
		temp +=DAY_MILLIS
	return arr

def round_timestamp(ts):
	dt = datetime.datetime.fromtimestamp(float(ts))
	d_truncated = datetime.date(dt.year, dt.month, dt.day)
	ts_rounded  = time.mktime(d_truncated.timetuple())
	return int(ts_rounded)

def date2timestamp(ts):
	dt = datetime.datetime.fromtimestamp(ts)
	return dt.strftime('%Y-%m-%d')

## mark as a fail attempt ##
def try_arrays_padding(items, since=0,until=0):
	since = int(float(since)*1000)
	until = int(float(until)*1000)
	
	for country_data in items.values():
		while country_data['values'][0][0] > since:
			datun = [float(country_data['values'][0][0])-86400000,0]
			country_data['values'].insert(0, datun)
		while country_data['values'][-1][0] < until:
			datun = [float(country_data['values'][-1][0])+86400000,0]
			country_data['values'].append(datun)
	
def arrays_padding(items, length):

	for country_data in items.values():
       	        while len(country_data['values']) < length:
               	        country_data['values'].insert(0,[country_data['values'][0][0]-86400000, 0])
                while len(country_data['values']) > length:
       	                country_data['values'].pop(0)


def validate_chartGraph(chart):
	try:
		data = chart['chartData']
		if not data:
			print "no data"
			return True

		length = len(data[0]['values'])
		arr = [i[0] for i in data[0]['values'] ]
		key = data[0]['key']
		for item in data:
			if not len(item['values']) == length:
				print "not the same lengths, ", item['key'], ":", len(item['values']), ", ", data[0]['key'],":",length 
				return False
                        for i,val in enumerate(item['values']):
                            if not val[0] in arr:
                                print "unrecognized time, ", item["key"], ", index: ", i
                print "OK Graph"
		return True
	except:
		traceback.print_exc(file=sys.stdout)
		return False
		


def get_top5_countries(chartData):
	top5 = []
        for country_data in chartData.values():
                country_rev = [float(country_data['total']),country_data['key']]
                if len(top5) < 5:
                        top5.append(country_rev)
                        top5.sort()
                else:
                        top5.insert(bisect_right(top5,country_rev), country_rev)
                        top5.pop(0)
        return [str(t[1]) for t in top5]
	

def unify_charts(charts):
        unified_chart = {}
	#print charts
        for p in charts:
                for c in p.values():
                        country = c['key']
                        if not unified_chart.has_key(country):
                                unified_chart[country] = c
                        else:
                                unified_chart[country]['values'] = [ [x[0],x[1]+y[1]] for x, y in zip(unified_chart[country]['values'], c['values'])]
                                unified_chart[country]['total'] += c['total']
	return unified_chart


### from himanshu's code : #####
def get_all_countries():
    all_countries = rankutils.all_countries()
    allcountry_result = {} 
    for countryData in all_countries:
        country_id = countryData['id']
        country_name = countryData['name']
        allcountry_result[country_id] = {}
        allcountry_result[country_id]['id'] = country_id
        allcountry_result[country_id]['name'] = country_name
        allcountry_result[country_id]['top'] = countryData['top']
    
    return allcountry_result


def get_user_creds(user, platform_name):
    for c in user.credentials_list.all():
        if c.content_object.platform == platform_name:
            return c
    return None

def is_duplicate_platform(user,platform):
    p = get_user_creds(user, platform)
    
    if p is None:
        return False
    else:
        return True

from services.facebook import facebook_service
from services.chartboost import chartboost_service
from services.admob import admob_service
from services.adx import adx_service
from services.vungle import vungle_service
from services.tapjoy import tapjoy_service
from services.adcolony import adcolony_service
from services.inmobi import inmobi_service

def get_service_by_platform(platform):
    
    platforms = { 'facebook'    : facebook_service(),
                  'chartboost'  : chartboost_service(),
                  'admob'       : admob_service(),
                  'adx'         : adx_service(),
                  'vungle'      : vungle_service(),
                  'tapjoy'      : tapjoy_service(),
                  'adcolony'    : adcolony_service(),
                  'inmobi'      : inmobi_service(),
                }
    
    return platforms[platform]


        


def __get_user_apps(user):
    apps = []
    cs = user.customer_set.all()
    for c in cs:
        apps.extend( AppInfo.objects.filter(customer_id=c.customer_id))
    return apps

########################################################################################

from django.conf import settings
from core.oauth.constants import SERVICE_ACCOUNT
from core.bigquery import get_client


def google_downloads_and_revenues(user_id, app_str,start_date, end_date):

    
    # BigQuery project id as listed in the Google Developers Console.
    project_id = 'mobbo-dashboard'
    service_account = SERVICE_ACCOUNT
    # PKCS12 or PEM key provided by Google.
    key = settings.GOOGLE_KEY
    client = get_client(project_id, service_account=service_account, private_key_file=key, readonly=True)
    
    MIN_DOWNLOADS = 300
    
    sql = "SELECT T1.country as country ,T1.downloads as downloads, T2.revenues as revenues\
          FROM (SELECT country, SUM(daily_user_installs) as downloads \
                FROM mobbo_dashboard.google_installation_report_records \
                WHERE customer_id = {0} AND \
                    package_name = '{1}' AND \
                    date >= '{2}' AND \
                    date <= '{3}' \
                GROUP BY country \
                ) T1 \
                LEFT JOIN  (SELECT buyer_country, SUM(developer_proceeds_usd) as revenues \
                            FROM mobbo_dashboard.google_report_records \
                            WHERE customer_id = {0} AND \
                                product_id = '{1}' AND \
                                charged_date >= '{2}' AND \
                                charged_date <= '{3}' \
                            GROUP BY buyer_country \
                            ) T2\
                            ON T1.country=T2.buyer_country \
            WHERE downloads > {4} \
                " .format(user_id, app_str, start_date, end_date, MIN_DOWNLOADS) 

    
    job_id, _results = client.query(sql)
    
    # Check if the query has finished running.
    complete, row_count = client.check_job(job_id)
    while not complete:
        complete, row_count = client.check_job(job_id)
    
    # Retrieve the results.
    results = client.get_query_rows(job_id)

    with open( "/tmp/google_downloads_and_revenues.table", "w+") as f:
        json.dump(results, f, indent = 4)

    return results


# Should be commented on production !
'''
def google_downloads_and_revenues(user_id, app_str,start_date, end_date):

    results = {}
    with open( "/tmp/google_downloads_and_revenues.table", "r") as f:
        results = json.load(f)
    
    return results
#'''    

# Should be commented on production !
'''
def itunes_downloads_and_revenues(user_id, app_str,start_date, end_date):
    
    results = {}
    with open( "/tmp/google_downloads_and_revenues.table", "r") as f:
        results = json.load(f)
    
    return results
#'''


def itunes_downloads_and_revenues(user_id, app_str,start_date, end_date):
    # BigQuery project id as listed in the Google Developers Console.
    project_id = 'mobbo-dashboard'
    service_account = SERVICE_ACCOUNT
    # PKCS12 or PEM key provided by Google.
    key = settings.GOOGLE_KEY
    client = get_client(project_id, service_account=service_account, private_key_file=key, readonly=True)
    
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
    
    MIN_DOWNLOADS = 300
    
    #'''
    sql ="SELECT country_code as country,  SUM(units) as downloads, SUM(developer_proceeds_usd) as revenues \
        FROM mobbo_dashboard.apple_report_records \
        WHERE begin_date >= '%s' AND \
              begin_date <= '%s' AND \
              customer_id = %d " % \
        (start_date,end_date,user_id)
        

    if sku is not None:
            sql += " AND (apple_identifier=%s OR parent_identifier='%s')" % (app_str,sku,)
    else:
            sql += " AND apple_identifier=%s " % (app_str,)
        
    sql += "GROUP BY country "
    
    sql += "HAVING downloads >= %d " % MIN_DOWNLOADS
    
    job_id, _results = client.query(sql)
    
    # Check if the query has finished running.
    complete, row_count = client.check_job(job_id)
    while not complete:
        complete, row_count = client.check_job(job_id)
    # Retrieve the results.
    results = client.get_query_rows(job_id)
    
    return results

#''' 


    
from dashboard.utils import product_info_for_auth_user, time_info_from_bounds

def _user_id(user):
  return user.id if user.is_authenticated() else settings.DEMO_AUTH_USER_ID

def _time_info(user, start_in_seconds, end_in_seconds):
  return time_info_from_bounds(_user_id(user), start_in_seconds, end_in_seconds)



def get_google_downloads_and_revenues(user, app_id, start_in_seconds, end_in_seconds):   
    app = AppInfo.objects.filter(app_info_id=app_id).first()
    
    timeInfo = _time_info(user, start_in_seconds, end_in_seconds)
    
    start_date = datetime.datetime.combine(timeInfo['start_date'], datetime.time.min)
    end_date = datetime.datetime.combine(timeInfo['end_date'], datetime.time.min)
                                
    response = google_downloads_and_revenues( user.id, app.app, start_date, end_date )  
 
    return response

def get_itunes_downloads_and_revenues(user, app_id, start_in_seconds, end_in_seconds): 
    
    app = AppInfo.objects.filter(app_info_id=app_id).first()
    
    timeInfo = _time_info(user, start_in_seconds, end_in_seconds)
    
    start_date = datetime.datetime.combine(timeInfo['start_date'], datetime.time.min)
    end_date = datetime.datetime.combine(timeInfo['end_date'], datetime.time.min)
                                
    response = itunes_downloads_and_revenues( user.id, app.identifier, start_date, end_date )  
    
    return response
    
def get_total_ad_revenues_by_country(user, app_info_id, since, until):
    
    app = AppInfo.objects.filter(app_info_id=app_info_id).first()
    
    app_fids = app.foreign_ids.all()
    
    since = round_timestamp(since)
    until = round_timestamp(until)
        
    totals = []
    for fid in app_fids:
        platform = fid.platform 
        app_id = fid.foreign_id
        service = get_service_by_platform(platform)
        total = service.get_total_ad_revenues_by_country(user, app_id, since=since, until=until)
        totals.append(total)

    ## unify countries:
    unified_json = {}
    for t in totals:
        for country, earned in t.items():
            country = countryCode2Name(country)
            if not country in unified_json:
                unified_json[country] =  earned
            else:
                unified_json[country] += earned

    return unified_json













