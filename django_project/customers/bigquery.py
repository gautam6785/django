import logging 
from core.bigquery import get_client
from core.bigquery.query_builder import render_query
from core.oauth.constants import GSUTIL_CLIENT_ID, GSUTIL_CLIENT_NOTSOSECRET, SERVICE_ACCOUNT
from core.timeutils import from_timestamp, utc_epoch, DATE_FMT
from datetime import date, datetime,time, timedelta
from pytz import timezone, utc
from django.conf import settings
from customers.models import Customer, CustomerExternalLoginInfo
from appinfo.constants import ANDROID_PLATFORM_STRING, IOS_PLATFORM_STRING
from appinfo.models import AppInfo, AppScreenshot

def getService():
	# BigQuery project id as listed in the Google Developers Console.
	project_id = 'mobbo-dashboard'
	service_account = SERVICE_ACCOUNT
	# PKCS12 or PEM key provided by Google.
	key = settings.GOOGLE_KEY
	client = get_client(project_id, service_account=service_account, private_key_file=key, readonly=False)
	
	return client
	
def apple_latest_record(customer_id, customer_account_id):
	
	client = getService()
	
	sql ="select * from mobbo_dashboard.apple_report_records where customer_id=%d and customer_account_id=%d order by begin_date desc limit 1" % \
		(customer_id,customer_account_id)
	
	job_id, _results = client.query(sql)
	
	# Check if the query has finished running.
	complete, row_count = client.check_job(job_id)
	while not complete:
            complete, row_count = client.check_job(job_id)
	results = client.get_query_rows(job_id)
	
	date = datetime.fromtimestamp(int(results[0]['begin_date'])).date()
	
	return date


def google_sales_latest_record(customer_id, customer_account_id):
	
	client = getService()
	sql ="select * from mobbo_dashboard.google_report_records where customer_id=%d and customer_account_id=%d order by charged_date desc limit 1" % \
		(customer_id,customer_account_id)
	
	job_id, _results = client.query(sql)
	
	# Check if the query has finished running.
	complete, row_count = client.check_job(job_id)
	while not complete:
            complete, row_count = client.check_job(job_id)
        
	results = client.get_query_rows(job_id)
	
	date = datetime.fromtimestamp(int(results[0]['charged_date'])).date()
	
	return date

def google_download_latest_record(customer_id, customer_account_id):
	client = getService()
	sql ="select * from mobbo_dashboard.google_installation_report_records where customer_id=%d and customer_account_id=%d order by date desc limit 1" % \
		(customer_id,customer_account_id)
	
	job_id, _results = client.query(sql)
	
	# Check if the query has finished running.
	complete, row_count = client.check_job(job_id)
	while not complete:
            complete, row_count = client.check_job(job_id)
        
	results = client.get_query_rows(job_id)
	
	date = datetime.fromtimestamp(int(results[0]['date'])).date()
	
	return date

# return customer google app packages list

def get_customer_google_app(app_customer_id, app_customer_account_id):
	
	appInfos = [ai for ai in AppInfo.objects.filter(customer_id=app_customer_id, customer_account_id=app_customer_account_id, platform='Google Play')]
	idToApp = {ai.app: ai for ai in appInfos}
	return idToApp


def get_single_app_revenue(app_customer_id, app_customer_account_id):
	
	appInfos = [ai for ai in AppInfo.objects.filter(customer_id=app_customer_id, customer_account_id=app_customer_account_id, platform='Google Play')]
	idToApp = {ai.app: ai for ai in appInfos}
	return idToApp

def get_customer_app(app_customer_id):
	appInfos = [ai for ai in AppInfo.objects.filter(customer_id=app_customer_id)]
	return appInfos

def get_app_revenue_download(customer_id,package,identifier,platform_type_id,sku):
	if platform_type_id==2:
		total_revenue = get_total_android_app_revenue(customer_id,package)
		#total_download = get_total_android_app_download(customer_id,package)
	
		print total_revenue	

def get_total_android_app_revenue(customer_id):
	client = getService()
	sql ="SELECT product_id, SUM(developer_proceeds_usd) as amount  FROM mobbo_dashboard.google_report_records WHERE customer_id = %d GROUP BY product_id" % \
		(customer_id)
	job_id, _results = client.query(sql)
	# Check if the query has finished running.
	complete, row_count = client.check_job(job_id)
	while not complete:
            complete, row_count = client.check_job(job_id)
        
	results = client.get_query_rows(job_id)
	return results

def get_total_itunes_app_revenue(customer_id,apps):
	client = getService()
	sql ="SELECT parent_identifier, SUM(developer_proceeds_usd) as amount FROM mobbo_dashboard.apple_report_records WHERE customer_id = %d and \
        parent_identifier IN (SELECT sku from mobbo_dashboard.apple_report_records where apple_identifier IN %s )GROUP BY parent_identifier" % \
        (customer_id, apps)
	job_id, _results = client.query(sql)
	# Check if the query has finished running.
	complete, row_count = client.check_job(job_id)
	while not complete:
            complete, row_count = client.check_job(job_id)
        
	results = client.get_query_rows(job_id)
	return results
	
def get_total_android_app_download(customer_id):
	client = getService()
	sql ="SELECT package_name, SUM(daily_user_installs) as daily_user_installs \
        FROM mobbo_dashboard.google_installation_report_records  WHERE customer_id = %d GROUP BY package_name" % \
        (customer_id)
	job_id, _results = client.query(sql)
	# Check if the query has finished running.
	complete, row_count = client.check_job(job_id)
	while not complete:
            complete, row_count = client.check_job(job_id)
        
	results = client.get_query_rows(job_id)
	return results

def get_total_itunes_app_download(customer_id):
	client = getService()
	sql ="SELECT apple_identifier, SUM(units) as units FROM mobbo_dashboard.apple_report_records WHERE customer_id = %d \
        AND units > 0 AND (product_type_identifier = '1F' OR product_type_identifier = '1') GROUP BY apple_identifier" % \
        (customer_id)
	job_id, _results = client.query(sql)
	# Check if the query has finished running.
	complete, row_count = client.check_job(job_id)
	while not complete:
            complete, row_count = client.check_job(job_id)
        
	results = client.get_query_rows(job_id)
	return results

def get_google_apps_download_data(start_date, end_date, customer_id):
	client = getService()
	sql = "SELECT package_name, SUM(daily_user_installs) as daily_user_installs FROM mobbo_dashboard.google_installation_report_records  WHERE date >= '%s' AND \
	      date <= '%s' AND customer_id = %d GROUP BY package_name" % \
		  (start_date, end_date, customer_id)
	job_id, _results = client.query(sql)
	# Check if the query has finished running.
	complete, row_count = client.check_job(job_id)
	while not complete:
            complete, row_count = client.check_job(job_id)
        
	results = client.get_query_rows(job_id)

	appdownloaddata = {}
	for result in results:
		appdownloaddata[result['package_name']] = {'download': result['daily_user_installs']}

	return appdownloaddata

def get_itunes_apps_download_data(start_date, end_date, customer_id):
	client = getService()
	sql = "SELECT apple_identifier, SUM(units) as units FROM mobbo_dashboard.apple_report_records WHERE begin_date >= '%s' AND begin_date <= '%s' AND customer_id = %d \
	    AND units > 0 AND (product_type_identifier = '1F' OR product_type_identifier = '1') GROUP BY apple_identifier" % \
		  (start_date,end_date,customer_id)
	job_id, _results = client.query(sql)
	# Check if the query has finished running.
	complete, row_count = client.check_job(job_id)
	while not complete:
            complete, row_count = client.check_job(job_id)
        
	results = client.get_query_rows(job_id)

	appdownloaddata = {}
	for result in results:
		appdownloaddata[int(result['apple_identifier'])] = {'download': result['units']}

	return appdownloaddata
	
	
def get_itunes_app_revenue_data(start_date,end_date,customer_id,apps):
	client = getService()
	sql ="SELECT parent_identifier, SUM(developer_proceeds_usd) as amount FROM mobbo_dashboard.apple_report_records WHERE begin_date >= '%s' AND begin_date <= '%s' AND customer_id = %d and \
        parent_identifier IN (SELECT sku from mobbo_dashboard.apple_report_records where apple_identifier IN %s )GROUP BY parent_identifier" % \
        (start_date, end_date, customer_id, apps)
	job_id, _results = client.query(sql)
	# Check if the query has finished running.
	complete, row_count = client.check_job(job_id)
	while not complete:
            complete, row_count = client.check_job(job_id)
        
	results = client.get_query_rows(job_id)
	
	apprevenuedata = {}
	for result in results:
		parent_identifier = result['parent_identifier']
		amount = result['amount']
		single_app =  AppInfo.objects.filter(customer_id=customer_id, sku=parent_identifier, platform='App Store').first()
		if single_app is None:
                    continue
		apple_identifier = single_app.identifier
		apprevenuedata[int(apple_identifier)] = {'revenue': amount}
	
	return apprevenuedata


def get_google_app_revenue_data(start_date,end_date,customer_id):
	client = getService()
	sql ="SELECT product_id, SUM(developer_proceeds_usd) as amount  FROM mobbo_dashboard.google_report_records WHERE charged_date >= '%s' AND charged_date <= '%s' AND customer_id = %d GROUP BY product_id" % \
        (start_date, end_date, customer_id)
	job_id, _results = client.query(sql)
	# Check if the query has finished running.
	complete, row_count = client.check_job(job_id)
	while not complete:
            complete, row_count = client.check_job(job_id)
        
	results = client.get_query_rows(job_id)
	
	apprevenuedata = {}
	for result in results:
		apprevenuedata[result['product_id']] = {'revenue': result['amount']}
		
	return apprevenuedata
