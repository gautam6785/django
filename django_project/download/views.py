import logging
import json
import simplejson
import requests
import csv
import os
import glob
import urllib
from django.db.models import Count
from appinfo import fetcher
from django.http import HttpResponse
from django.shortcuts import render
from customers.models import Customer, CustomerExternalLoginInfo
from django.shortcuts import render_to_response

from core.timeutils import from_timestamp, utc_epoch, DATE_FMT
from datetime import date, datetime,time, timedelta
from pytz import timezone, utc
import re
from dateutil import parser
from base64 import b64encode
from boto import connect_gs, storage_uri
from boto.exception import InvalidUriError
from core.currency import convert_decimal_to_usd
from core.db.constants import TEN_PLACES, TWO_PLACES
from core.oauth import scriber_gcs_boto_plugin
from core.oauth.constants import GSUTIL_CLIENT_ID, GSUTIL_CLIENT_NOTSOSECRET, SERVICE_ACCOUNT
from decimal import Decimal
from django.db import transaction
from metrics.models import GoogleReportRecord, AppleReportRecord
from metrics.salesreports import ReportUnavailableException
from metrics.googlesalesreports import fetch_google_daily_sales_report, fetch_google_report, fetch_google_app_packages_name

from metrics.googleinstallreports import fetch_google_install_report

from os import urandom
from pytz import utc
from re import match
from StringIO import StringIO
from zipfile import ZipFile
from django.conf import settings
from core.db.dynamic import connection
import urllib2
from dateutil import parser
from dashboard import google_crawlplay

from appinfo.constants import ANDROID_PLATFORM_STRING, IOS_PLATFORM_STRING
from appinfo.models import AppInfo, AppScreenshot
import zlib
from django.db.models import Sum
from django.db.models import Q
from core.bigquery import get_client
from core.bigquery.query_builder import render_query
from oauth2client.client import GoogleCredentials
#from gcloud import bigquery
#from gcloud.bigquery import SchemaField
from metrics.salesreports import fetch_apple_daily_sales_report, ReportUnavailableException
from download.big_query import BigQuery
from customers import bigquery
from django.core.mail import send_mail


_4_AM = time(4, 0)

_ITUNES_DEVELOPER_REVENUE_SHARE = Decimal('0.7')
_ITUNES_FEE = Decimal('0.3')
_ANDROID_APP_INFO_URL = 'http://mobbo.com/Android/AppDetails/%s'
logger = logging.getLogger(__name__)

_DEFAULT_CURRENCY = 'USD'
_CURRENCT_CONVERTER_URL = 'http://currencies.apps.grandtrunk.net/getrate'

_GOOGLE_APP_UPDATE_MERCHANT_CURRENCY = """
  SELECT 
     product_id
  FROM
    google_report_records
  WHERE
    merchant_currency IS NULL AND charged_date >= %s AND charged_date <= %s AND customer_id = '%s'
  GROUP BY
    product_id	
  ;
  """



_APPLE_REPORT_URL_BASE = "https://reportingitc.apple.com/autoingestion.tft?"
_APPLE_REPORT_HEADERS = {"Content-Type" : "application/x-www-form-urlencoded"}  
_APPLE_REPORT_EXPECTED_FIELDS = [
  'Provider',                #  0
  'Provider Country',        #  1
  'SKU',                     #  2
  'Developer',               #  3
  'Title',                   #  4
  'Version',                 #  5
  'Product Type Identifier', #  6
  'Units',                   #  7
  'Developer Proceeds',      #  8
  'Begin Date',              #  9
  'End Date',                # 10
  'Customer Currency',       # 11
  'Country Code',            # 12
  'Currency of Proceeds',    # 13
  'Apple Identifier',        # 14
  'Customer Price',          # 15
  'Promo Code',              # 16
  'Parent Identifier',       # 17
  'Subscription',            # 18
  'Period',                  # 19
  'Category',                # 20
  'CMB',                     # 21
  'Device',                  # 22
  'Supported Platforms',     # 23
]

_ANDROID_APP_INFO_URL = 'http://mobbo.com/Android/AppDetails/%s'

# Create your views here.
def single_app_revenue(request):
    
    user = request.user
    customer = Customer.objects.get(auth_user=user)
    customer_id = customer.customer_id
    
    appInfos = AppInfo.objects.filter(customer_id=customer_id)

    todayUtc = from_timestamp(utc_epoch(), utc).date()
    startDate = todayUtc - timedelta(days=24)

    start_date = datetime.combine(startDate, time.min)
    end_date = datetime.combine(todayUtc, time.min)
	
    appInfos = [ai for ai in AppInfo.objects.filter(customer_id=customer_id, platform='App Store')]
    idToApp = {int(ai.identifier): ai for ai in appInfos}
    apps = (tuple(idToApp))
	
    single_app =  AppInfo.objects.filter(customer_id=customer_id, sku="air.com.pegasgames.wheely5", platform='App Store').first()
    
    print single_app.name
    
    googleAppdownload = bigquery.get_google_apps_download_data(start_date, end_date, customer_id)
    itunesAppdownload = bigquery.get_itunes_apps_download_data(start_date, end_date, customer_id)
    
    #itunesApprevenue = bigquery.get_itunes_app_revenue_data(start_date, end_date, customer_id, apps)
    appData = {}
    for appinfo in appInfos:
        platform_type_id = appinfo.platform_type_id.platform_type_id
        if platform_type_id == 2:
            download = googleAppdownload[appinfo.app]['download'] if googleAppdownload.has_key(appinfo.app) else 0
        else:
            download = itunesAppdownload[int(appinfo.identifier)]['download'] if itunesAppdownload.has_key(int(appinfo.identifier)) else 0
            #print int(appinfo.identifier)
            #download = itunesAppdownload[int(appinfo.identifier)]['download'] if itunesAppdownload[int(appinfo.identifier)] else 0
        appData[appinfo.app_info_id] =  {
            'name' : appinfo.name,
            'id' : appinfo.app_info_id,
            'icon_url': appinfo.icon_url,
            'platform': appinfo.platform,
            'total_download': int(download),
        }

    #print appData

    """
    ############# Get itunes total download data ########
    itune_downloads = bigquery.get_total_itunes_app_download(customer_id) 
    for itune_download in itune_downloads:
        apple_identifier = itune_download['apple_identifier']
        units = int(itune_download['units'])
        AppInfo.objects.filter(identifier = apple_identifier,customer_id=customer_id,platform_type_id=1).update(total_downloads = units)
    
    
    ############# Get android total download data ########
    android_downloads = bigquery.get_total_android_app_download(customer_id) 
    for android_download in android_downloads:
        download = android_download['daily_user_installs']
        package = android_download['package_name']
        AppInfo.objects.filter(app = package,customer_id=customer_id,platform_type_id=2).update(total_downloads = download)
    
    
    ###### Get itunes app revenue #######
    itune_revenue = bigquery.get_total_itunes_app_revenue(customer_id, apps)
    for revenue in itune_revenue:
        amount = revenue['amount']
        parent_identifier = revenue['parent_identifier']
        AppInfo.objects.filter(sku = parent_identifier,customer_id=customer_id,platform_type_id=1).update(total_revenue = amount)
    
   
   
    ###### Get Google play app revenue ################ 
    android_revenue = bigquery.get_total_android_app_revenue(customer_id)
    for revenue in android_revenue:
        amount = revenue['amount']
        product_id = revenue['product_id']
        AppInfo.objects.filter(app = product_id,customer_id=customer_id,platform_type_id=2).update(total_revenue = amount)
    
    """

    return render(request, "download/test.html")

# Create your views here.
def get_app_sku(request):
    
    # BigQuery project id as listed in the Google Developers Console.
    project_id = 'mobbo-dashboard'
    service_account = SERVICE_ACCOUNT
    # PKCS12 or PEM key provided by Google.
    key = settings.GOOGLE_KEY
    
    client = get_client(project_id, service_account=service_account, private_key_file=key, readonly=False)
    appinfos = AppInfo.objects.filter(customer_id=1, customer_account_id=2)
    
    for app in appinfos:
        identifier = app.identifier
        print identifier
        sql ="SELECT sku \
        FROM mobbo_dashboard.apple_report_records WHERE apple_identifier = %d and customer_id = 1 limit 1" %(identifier)
        job_id, _results = client.query(sql)
        # Check if the query has finished running.
        complete, row_count = client.check_job(job_id)
        # Retrieve the results.
        results = client.get_query_rows(job_id)
        sku =  results[0]['sku']
        print sku
        AppInfo.objects.filter(customer_id=1, customer_account_id=2, identifier = identifier).update(sku=sku)
        
    return render(request, "download/test.html")    

# Create your views here.
def sales_reports(request):	
	login_info_id = 1
	loginInfo = CustomerExternalLoginInfo.objects.get(pk=login_info_id)
	customerId = loginInfo.customer_id
	
	todayUtc = from_timestamp(utc_epoch(), utc).date()
	yesterdayUtc = todayUtc - timedelta(days=1)
	#startDate = todayUtc - timedelta(days=50)
	startDate = date(2016,05,15)
	endDate = yesterdayUtc
	
	file_path = '/'.join([settings.GOOGLE_PLAY_UPLOAD_FOLDER, 'sales', str(customerId.customer_id), str(login_info_id)])
	if not os.path.exists(file_path):
		os.makedirs(file_path) 
	
	if os.path.isfile(file_path+'/google_report_reports.csv'):
		os.remove(file_path+'/google_report_reports.csv')
		
	records = fetch_google_report(loginInfo.refresh_token, loginInfo.gc_bucket_id, 'sales',
        startDate, endDate, customerId, app_id=None)
	
	
	#appInfos = [ai for ai in AppInfo.objects.filter(customer_id=customerId, customer_account_id=loginInfo.login_info_id, platform='Google Play')]
	
	"""
	idToApp = {ai.app: ai for ai in appInfos}
	for record in records:
		productId = record['product_id']
		if productId not in idToApp:
			fetcher.ANDROID_APP_INFO_FETCHER.fetch(productId,customerId,loginInfo)
	"""
	writer = csv.writer(open(file_path+'/google_report_reports.csv', 'w'))
	for rec in records:
		writer.writerow([rec['customer_id'], login_info_id, rec['order_number'], rec['charged_date'], rec['charged_time'], rec['financial_status'], rec['device_model'] ,rec['product_title'], rec['product_id'], rec['product_type'],
						 rec['sku_id'], rec['sale_currency'], rec['item_price'], rec['taxes'], rec['charged_amount'], rec['developer_proceeds'], rec['developer_proceeds_usd'], rec['buyer_city'], rec['buyer_state'],
						 rec['buyer_postal_code'], rec['buyer_country'], rec['timestamp'], rec['creation_time'], rec['last_modified']])
				 
	return render(request, "download/test.html")
	
def install_reports(request):
    loginId = 1
    login = CustomerExternalLoginInfo.objects.get(pk=loginId)
    customer = login.customer_id
    
    todayUtc = from_timestamp(utc_epoch(), utc).date()
    yesterdayUtc = todayUtc - timedelta(days=1)
    #startDate = todayUtc - timedelta(days=30)
    startDate = date(2016,05,15)
    endDate = yesterdayUtc
    
    """
    records = fetch_google_report(login.refresh_token, login.gc_bucket_id, 'installs',
        startDate, endDate, customer, app_id=None)
    
    filename = "google_installation_report.csv"
    folder = '/'.join([settings.GOOGLE_PLAY_UPLOAD_FOLDER, 'installs', str(customer.customer_id), str(loginId)])
    file_path = '/'.join([settings.GOOGLE_PLAY_UPLOAD_FOLDER, 'installs', str(customer.customer_id), str(loginId), filename])
    
    if not os.path.exists(folder):
        os.makedirs(folder) 
    
    if os.path.isfile(file_path):
        os.remove(file_path)
    
    fSubset = open(file_path, 'w')
    os.chmod(file_path, 0o777)    
    writer = csv.writer(fSubset)
    
    
    
    packagelist = []
    sku=None
    for rec in records:
        package = rec['package_name']
        if package not in packagelist:
            fetcher.ANDROID_APP_INFO_FETCHER.fetch(package,sku,customer,login)
            packagelist.append(package)
                
        writer.writerow([rec['customer_id'], loginId, rec['record_date'], rec['package_name'], rec['country'], rec['current_device_installs'], rec['daily_device_installs'] ,rec['daily_device_uninstalls'], 
                        rec['daily_device_upgrades'], rec['current_user_installs'], rec['total_user_installs'], rec['daily_user_installs'], rec['daily_user_uninstalls'], rec['creation_time'],
                        rec['last_modified']])
    fSubset.close()
    """
    # Import Csv File
    """
    if os.path.isfile(file_path):
        os.chmod(file_path, 0o777)
        logger.info('import install csv file in bigquery %s' % file_path)
        BigQuery.insert_googleinstallCSV(file_path,'staging_google_installation_report_records')
    
    """
    
    apps = bigquery.get_customer_google_app(customer,loginId)
    
    for app in apps:
        records = fetch_google_report(login.refresh_token, login.gc_bucket_id, 'installs', startDate, endDate, customer, app_id=app)
        filename = "google_installation_report_%s.csv" %(app)
        folder = '/'.join([settings.GOOGLE_PLAY_UPLOAD_FOLDER, 'installs', str(customer.customer_id), str(loginId)])
        file_path = '/'.join([settings.GOOGLE_PLAY_UPLOAD_FOLDER, 'installs', str(customer.customer_id), str(loginId), filename])
        if not os.path.exists(folder):
            os.makedirs(folder) 
        if os.path.isfile(file_path):
            os.remove(file_path)
        
        fSubset = open(file_path, 'w')
        os.chmod(file_path, 0o777)    
        writer = csv.writer(fSubset)
        for rec in records:
            writer.writerow([rec['customer_id'], loginId, rec['record_date'], rec['package_name'], rec['country'], rec['current_device_installs'], rec['daily_device_installs'] ,rec['daily_device_uninstalls'], 
                rec['daily_device_upgrades'], rec['current_user_installs'], rec['total_user_installs'], rec['daily_user_installs'], rec['daily_user_uninstalls'], rec['creation_time'],
                            rec['last_modified']])
        fSubset.close()
        
        if os.path.isfile(file_path):
            os.chmod(file_path, 0o777)
            logger.info('import install csv file in bigquery %s' % file_path)
            BigQuery.insertCSV(file_path,'google_installation_report_records')
    
    """
    #records = fetch_google_install_report(loginInfo.refresh_token, loginInfo.gc_bucket_id, startDate, endDate, customerId)
    
    records = fetch_google_report(loginInfo.refresh_token, loginInfo.gc_bucket_id, 'installs', startDate, endDate, customerId, app_id=None)
    
    file_path = '/'.join([settings.GOOGLE_PLAY_UPLOAD_FOLDER, 'installs', str(customerId.customer_id), str(login_info_id)])
    if not os.path.exists(file_path):
        os.makedirs(file_path) 
        
    if os.path.isfile(file_path+'/google_installation_report_reports.csv'):
        os.remove(file_path+'/google_installation_report_reports.csv')
        
    appInfos = [ai for ai in AppInfo.objects.filter(customer_id=customerId, customer_account_id=loginInfo.login_info_id, platform='Google Play')]
    idToApp = {ai.app: ai for ai in appInfos}
    
    for record in records:
        productId = record['package_name']
        if productId not in idToApp:
            fetcher.ANDROID_APP_INFO_FETCHER.fetch(productId,customerId,loginInfo)
            
    writer = csv.writer(open(file_path+'/google_installation_report_reports.csv', 'w'))
    for rec in records:
        writer.writerow([rec['customer_id'], rec['record_date'], rec['package_name'], rec['country'], rec['current_device_installs'], rec['daily_device_installs'] ,rec['daily_device_uninstalls'], 
                        rec['daily_device_upgrades'], rec['current_user_installs'], rec['total_user_installs'], rec['daily_user_installs'], rec['daily_user_uninstalls'], rec['creation_time'],
                        rec['last_modified']])
    """
    return render(request, "download/test.html")

def app_list(request):
    user = request.user
    itunes_accounts = []
    google_play_accounts = []
    
    try:
        customer = Customer.objects.get(auth_user=user)
    except Customer.DoesNotExist:
        customer = None
    
    if customer is not None:
        connected_accounts = CustomerExternalLoginInfo.objects.filter(customer_id=customer.customer_id,is_active=True)
        for c in connected_accounts:
            appinfo = AppInfo.objects.filter(customer_id=c.login_info_id)
            app_count = appinfo.count()
            app_icon = []
            for app in appinfo:
                icon = app.icon_url
                app_icon.append({'icon': icon})
            copied_c = {}
            copied_c['username'] = c.username
            copied_c['external_service'] = c.external_service
            copied_c['creation_time'] = c.creation_time
            copied_c['app_count'] = app_count
            copied_c['icon'] = app_icon
            
            if c.external_service == 'iTunes Connect':
                itunes_accounts.append(copied_c)
            if c.external_service == 'Google Cloud':
                google_play_accounts.append(copied_c)
	return render(request, "download/test.html")

# Create your views here.
def reports(request):
    login_info_id = 1
    loginInfo = CustomerExternalLoginInfo.objects.get(pk=login_info_id)
    customerId = loginInfo.customer_id
    todayUtc = from_timestamp(utc_epoch(), utc).date()
    yesterdayUtc = todayUtc - timedelta(days=1)
    #startDate = todayUtc - timedelta(days=30)
    startDate = date(2011,11,27)
    #startDate = date(2016,05,16)
    endDate = yesterdayUtc
    testdate = date(2015,11,27)
    
    records = fetch_google_report(loginInfo.refresh_token, loginInfo.gc_bucket_id, 'sales',
        startDate, endDate, customerId, app_id=None)
    
    """
    # BigQuery project id as listed in the Google Developers Console.
    project_id = 'mobbo-dashboard'
    service_account = SERVICE_ACCOUNT
    
    # PKCS12 or PEM key provided by Google.
    key = settings.GOOGLE_KEY
    
    client = get_client(project_id, service_account=service_account, private_key_file=key, readonly=False)
    """
    
    outfile_path = '/var/www/Projects/mobbo-dashboards2/django_project/keyset/google_report_reports.csv'
    writer = csv.writer(open(outfile_path, 'w'))
    for record in records:
        customer_id = record['customer_id']
        order_number = record['order_number']
        charged_date = record['charged_date']
        charged_time = record['charged_time']
        financial_status = record['financial_status']
        device_model = record['device_model']
        product_title = record['product_title']
        product_id = record['product_id']
        product_type = record['product_type']
        sku_id = record['sku_id']
        sale_currency = record['sale_currency']
        item_price = record['item_price']
        taxes = record['taxes']
        charged_amount = record['charged_amount']
        buyer_city = record['buyer_city']
        buyer_state = record['buyer_state']
        buyer_postal_code = record['buyer_postal_code']
        buyer_country = record['buyer_country']
        timestamp = record['timestamp']
        developer_proceeds = record['developer_proceeds']
        developer_proceeds_usd = record['developer_proceeds_usd']
        creation_time = record['creation_time']
        last_modified = record['last_modified']
        
        writer.writerow([customer_id, order_number, charged_date, charged_time, financial_status, device_model, product_title, product_id, product_type, sku_id, sale_currency, 
                item_price, taxes, charged_amount, developer_proceeds, developer_proceeds_usd, buyer_city, buyer_state, buyer_postal_code, buyer_country, timestamp, creation_time, last_modified])
    
    
    """
    job = client.import_data_from_uris( [outfile_path],
                                    'mobbo_dashboard',
                                    'google_report_records',
                                    source_format='CSV')
    
    try:
        job_resource = client.wait_for_job(job, timeout=60)
        print job_resource
    except BigQueryTimeoutException:
        print "Timeout"
    
    """
    """
    inserted = client.push_rows('mobbo_dashboard', 'google_report_records', records)
    print inserted
    
    """
    
    """
    appInfos = [ai for ai in AppInfo.objects.filter(customer_id=customerId, platform='Google Play')]
    idToApp = {ai.app: ai for ai in appInfos}
    for record in records:
        productId = record.product_id
        #productId = record.package_name
        if productId not in idToApp:
            appInfo = fetcher.ANDROID_APP_INFO_FETCHER.fetch(productId,customerId)
    """
    #print records
    
    """
    scriber_gcs_boto_plugin.SetAuthInfo(refresh_token)
    reportFolder = _report_folder(report_type)
    
    LOCAL_PATH = '/'.join([settings.GOOGLE_PLAY_UPLOAD_FOLDER, reportFolder, str(customerId.customer_id), str(login_info_id)])
    reportLocation = '/'.join([_GOOGLE_REPORT_BUCKET_BASE + bucket_id])
    
    src_uri = storage_uri(reportLocation)
    
    #Creates a local folder if not already exists
    
    if not os.path.exists(LOCAL_PATH):
        os.makedirs(LOCAL_PATH) 
    for key in src_uri.list_bucket(reportFolder):
        key_name = key.name
        
        # Get the filename
        filename = key_name.split('/')[-1]
        key.get_contents_to_filename(LOCAL_PATH+'/'+filename)
    """
    return render(request, "download/test.html")
    
    #return render_to_response('download/report.html',{'loginInfos':loginInfo,'records':records})
    #return HttpResponse(json.dumps({"message":"test message"}),
                #content_type='application/json')
    

def itunes_reports(request):
    login_info_id = 2
    loginInfo = CustomerExternalLoginInfo.objects.get(pk=login_info_id)
    customerId = loginInfo.customer_id
    
    tz = timezone('America/Los_Angeles')
    todayLocal = from_timestamp(utc_epoch(), tz).date()
    yesterdayLocal = todayLocal - timedelta(days=1)
    
    startDate = date(2016,07,26)
    #startDate = todayLocal - timedelta(days=30)
    endDate = yesterdayLocal - timedelta(days=0)
    
    start_date_str=str(startDate)
    end_date_str=str(endDate)
    doneToken = b64encode(urandom(20)).rstrip('==')
    
    """
    vendor_id your unique vendor number.
    report_type Sales or Newsstand. 
    date_type Daily, Weekly, Monthly, Yearly.
    report_subtype Summary, Detailed, or Opt-In.Opt-In only applies to Sales report
    date (optional) YYYYMMDD (Daily or Weekly).YYYYMM (Monthly) YYYY (Yearly).The date of the report you are requesting. Date parameter is optional. If it is not provided, you
    will get the latest report available
    https://www.apple.com/itunesnews/docs/AppStoreReportingInstructions.pdf
    """
    
    reportDate = parser.parse(start_date_str).date()
    username = loginInfo.username
    password = loginInfo.password
    vendor_id = loginInfo.apple_vendor_id
    #report_date_str = endDate.strftime('%Y%m%d')
    date_type='Daily'
    report_subtype='Summary'
    report_type='Sales'
    
    startDate = parser.parse(start_date_str).date()
    endDate = parser.parse(end_date_str).date()
    
    records = []
    for delta in range((endDate - startDate).days + 1):
        reportDate = startDate + timedelta(days=delta)
        #report_date_str = reportDate.strftime('%Y%m%d')
        reportDateStr = str(reportDate)
        reportDate = parser.parse(reportDateStr).date()
        print reportDate
        #fileRecords = itunes_records(username,password,vendor_id,report_type,date_type,report_subtype,report_date_str,customerId)
        fileRecords = fetch_apple_daily_sales_report(username,password,vendor_id,reportDate)
        if fileRecords:
            records.extend(fileRecords)

    file_path = '/'.join([settings.ITUNES_UPLOAD_FOLDER, 'sales', str(customerId.customer_id), str(login_info_id)])
    if not os.path.exists(file_path):
        os.makedirs(file_path) 
        
    if os.path.isfile(file_path+'/apple_report_reports.csv'):
        os.remove(file_path+'/apple_report_reports.csv')
    
    writer = csv.writer(open(file_path+'/apple_report_reports.csv', 'w'))
    for rec in records:
        writer.writerow([customerId.customer_id, login_info_id, rec['apple_identifier'], rec['provider'], rec['provider_country'], rec['sku'], rec['developer'] ,rec['title'], rec['version'], rec['product_type_identifier'],
            rec['units'], rec['developer_proceeds'], rec['developer_proceeds_usd'], rec['begin_date'], rec['end_date'], rec['customer_currency'], rec['country_code'], rec['currency_of_proceeds'], rec['customer_price'],
            rec['promo_code'], rec['parent_identifier'], rec['subscription'], rec['period'], rec['category'],rec['cmb'],rec['device'],rec['supported_platforms']])
                
    """
    records = sorted(records, key=lambda x: x['begin_date'],reverse=True)
    outfile_path = '/var/www/Projects/mobbo-dashboards2/django_project/keyset/apple_report_reports.csv'
    writer = csv.writer(open(outfile_path, 'w'))
    appInfos = [ai for ai in AppInfo.objects.filter(customer_id=customerId, platform='App Store')]
    identifierToProduct = {ai.identifier: ai for ai in appInfos}
    for record in records:
        apple_identifier = record['apple_identifier']
        if apple_identifier not in identifierToProduct:
            appInfo = fetcher.IOS_ID_APP_INFO_FETCHER.fetch(apple_identifier, customerId)
            
        customer_id = record['customer_id']
        apple_identifier = record['apple_identifier']
        provider = record['provider']
        provider_country = record['provider_country']
        sku = record['sku']
        developer = record['developer']
        title = record['title']
        version = record['version']
        product_type_identifier = record['product_type_identifier']
        units = record['units']
        developer_proceeds = record['developer_proceeds']
        developer_proceeds_usd = record['developer_proceeds_usd']
        begin_date = record['begin_date']
        end_date = record['end_date']
        customer_currency = record['customer_currency']
        country_code = record['country_code']
        currency_of_proceeds = record['currency_of_proceeds']
        customer_price = record['customer_price']
        promo_code = record['promo_code']
        parent_identifier = record['parent_identifier']
        subscription = record['subscription']
        period = record['period']
        category = record['category']
        cmb = record['cmb']
        device = record['device']
        supported_platforms = record['supported_platforms']
        writer.writerow([customer_id, apple_identifier, provider, provider_country, sku, developer, title, version, product_type_identifier, units, developer_proceeds,developer_proceeds_usd, 
                        begin_date, end_date, customer_currency, country_code, currency_of_proceeds, customer_price, promo_code, parent_identifier, subscription, period, category, cmb, device, supported_platforms])
    
    """	
    """"
        appInfos = [ai for ai in AppInfo.objects.filter(customer_id=customerId, platform='App Store')]
        identifierToProduct = {ai.identifier: ai for ai in appInfos}
        for record in records:
            identifier = record.apple_identifier
            if identifier not in identifierToProduct:
                appInfo = fetcher.IOS_ID_APP_INFO_FETCHER.fetch(identifier, customerId)
    """
    """
    records = itunes_records(username,password,vendor_id,report_type,date_type,report_subtype,report_date_str)
    appInfos = [ai for ai in AppInfo.objects.filter(customer_id=customerId, platform='App Store')]
    identifierToProduct = {ai.identifier: ai for ai in appInfos}
    for record in records:
        identifier = record.apple_identifier
        if identifier not in identifierToProduct:
            appInfo = fetcher.IOS_ID_APP_INFO_FETCHER.fetch(identifier, customerId)
    """		
    return render(request, "download/test.html")


def itunes_records(username,password,vendor_id,report_type,date_type,report_subtype,report_date_str,customerId):
	
	params = ({
		"USERNAME" : username,
		"PASSWORD" : password,
		"VNDNUMBER" : vendor_id,
		"TYPEOFREPORT" : report_type,
		"DATETYPE" : date_type,
		"REPORTTYPE" : report_subtype,
		"REPORTDATE" : report_date_str
	})
	
	response = requests.post(_APPLE_REPORT_URL_BASE, headers=_APPLE_REPORT_HEADERS, params=params)
	
	if 'errormsg' in response.headers and response.headers['errormsg']:
		# For now, assume all 2XX status codes represent report unavailable exceptions.
		if response.ok:
			logger.warning('fetch_apple_report failed with remote error message %s' %
				response.headers['errormsg'])
			raise ReportUnavailableException('Report not yet available')
		else:
			raise ReportFetchException(response.headers['errormsg'])
	elif 'filename' in response.headers and response.headers['filename']:
		decompressed_data=zlib.decompress(response.content, 16+zlib.MAX_WBITS)
		reader = csv.reader(decompressed_data.splitlines(), delimiter='\t')
		
		records = []
		for i, row in enumerate(reader):
			salesData = {}
			if i == 0:
				if _APPLE_REPORT_EXPECTED_FIELDS != row[:len(_APPLE_REPORT_EXPECTED_FIELDS)]:
					logger.warning('Encountered unexpected apple report fields: %s' % row)
					break
			else:
				salesData['customer_id'] = int(customerId.customer_id)
				salesData['provider'] = row[0]
				salesData['provider_country'] = row[1]
				salesData['sku'] = row[2]
				salesData['developer'] = row[3] if row[3] != '' else None
				salesData['title'] = row[4]
				salesData['version'] = row[5] if row[5] != '' else None
				salesData['product_type_identifier'] = row[6]
				units = Decimal(row[7]).quantize(TWO_PLACES)
				developer_proceeds = Decimal(row[8]).quantize(TWO_PLACES)
				currency_of_proceeds = row[13]			
				beginDate = parser.parse(row[9]).date()
				begin_date = datetime.combine(beginDate, time.min)
				salesData['begin_date'] = str(begin_date)
				endDate = parser.parse(row[10]).date()
				end_date = datetime.combine(endDate, time.min)
				salesData['end_date'] = str(end_date)
				salesData['customer_currency'] = row[11]
				salesData['country_code'] = row[12]
				salesData['currency_of_proceeds'] = row[13]
				salesData['apple_identifier'] = long(row[14])
				salesData['customer_price'] = str(_parse_decimal(row[15]))
				salesData['promo_code'] = row[16] if row[16] != '' else None
				salesData['parent_identifier'] = row[17] if row[17] != '' else None
				salesData['subscription'] = row[18] if row[18] != '' else None
				salesData['period'] = row[19] if row[19] != '' else None
				salesData['category'] = row[20]
				salesData['cmb'] = row[21] if row[21] != '' else None
				salesData['device'] = row[22] if row[22] != '' else None
				salesData['supported_platforms'] = row[23] if row[23] != '' else None
				
				total_developer_proceeds = units * developer_proceeds
				developerProceeds = total_developer_proceeds * _ITUNES_DEVELOPER_REVENUE_SHARE
				developerProceedsUsd = convert_decimal_to_usd(developerProceeds,
					currency_of_proceeds).quantize(TEN_PLACES)
				
				salesData['units'] = str(units)
				salesData['developer_proceeds'] = str(developerProceeds)
				salesData['developer_proceeds_usd'] = str(developerProceedsUsd)
				
				records.append(salesData)	
				"""
				records.append(AppleReportRecord(
				  customer_id=customerId, provider=provider, provider_country=provider_country, sku=sku, developer=developer,
				  title=title, version=version, product_type_identifier=product_type_identifier,
				  units=units, developer_proceeds=developer_proceeds, begin_date=begin_date,
				  end_date=end_date, customer_currency=customer_currency, country_code=country_code,
				  currency_of_proceeds=currency_of_proceeds, apple_identifier=apple_identifier,
				  customer_price=customer_price, promo_code=promo_code, parent_identifier=parent_identifier,
				  subscription=subscription, period=period, category=category, cmb=cmb,device=device,supported_platforms=supported_platforms,
				  developer_proceeds_usd=developer_proceeds_usd))
				"""
		return records

def _parse_decimal(value_str):
	decimalStr = value_str.replace(',', '')
	return Decimal(decimalStr)

def test_query(request):
	tz = timezone('America/Los_Angeles')
	todayLocal = from_timestamp(utc_epoch(), tz).date()
	yesterdayLocal = todayLocal - timedelta(days=1)
	startDate = date(2016,04,03)
	#endDate = yesterdayLocal - timedelta(days=1)
	endDate = date(2016,04,03)
	start_date_str=str(startDate)
	end_date_str=str(endDate)
	
	appleReportObject = AppleReportRecord.objects.filter(apple_identifier=1051252134).values('sku').first()
	sku = appleReportObject['sku']
	
	"""
	records = AppleReportRecord.objects.all()\
				.filter(begin_date__gte=start_date_str)\
				.filter(begin_date__lte=end_date_str)\
				.filter(units__gte=0)\
				.filter(developer_proceeds_usd__gt=0)\
				.values('begin_date','country_code')\
				.annotate(Sum('developer_proceeds_usd'))\
				.annotate(count=Count('begin_date'))\
				.order_by('begin_date')
	"""
	
	records = AppleReportRecord.objects.all()\
				.filter(begin_date__gte=start_date_str)\
				.filter(begin_date__lte=end_date_str)\
				.filter(units__gte=0)\
				.filter(developer_proceeds_usd__gt=0)\
				.values('begin_date','country_code')\
				.annotate(amount=Sum('developer_proceeds_usd'))\
				.values('begin_date','country_code','amount','country_code__display_name')\
				.order_by('begin_date')
	
	if sku is not None:
		records = records.filter(Q(apple_identifier='1051252134') | Q(parent_identifier=sku))
	else:
		records = records.filter(apple_identifier='1051252134')
	
	
	"""
	records = GoogleReportRecord.objects.all()\
				.filter(charged_date__gte=start_date_str)\
				.filter(charged_date__lte=end_date_str)\
				.filter(customer_id=1)\
				.filter(units__gte=0)\
				.filter(developer_proceeds_usd__gt=0)\
				.values('begin_date','country_code')\
				.annotate(Sum('developer_proceeds_usd'))\
				.annotate(count=Count('begin_date'))\
				.order_by('begin_date')
	
	
	"""
	#data = records.select_related("Country")
	print records
	#for record in records:
		#print record['country_code__display_name']
	return render(request, "download/test.html")


def big_query(request):
    
    # BigQuery project id as listed in the Google Developers Console.
    project_id = 'mobbo-dashboard'
    service_account = SERVICE_ACCOUNT
	
    # PKCS12 or PEM key provided by Google.
    key = settings.GOOGLE_KEY
    client = get_client(project_id, service_account=service_account, private_key_file=key, readonly=False)

    tz = timezone('America/Los_Angeles')
    todayLocal = from_timestamp(utc_epoch(), tz).date()
    yesterdayLocal = todayLocal - timedelta(days=1)
    #startDate = todayLocal - timedelta(days=30)
    endDate = yesterdayLocal - timedelta(days=1)
    login_info_id = 1
    #CustomerExternalLoginInfo.objects.filter(login_info_id = login_info_id).update(latest_report = date)
    
    loginInfo = CustomerExternalLoginInfo.objects.get(pk=login_info_id)
    customer = loginInfo.customer_id
    
    date = bigquery.google_download_latest_record(customer.customer_id,login_info_id)
    
    startDate = date + timedelta(days=1)
    start_date_str=str(startDate)
    end_date_str=str(endDate)
    
    """
    filename = "apple_report_records_%s.txt" %(start_date_str)
    file_path = '/'.join([settings.ITUNES_UPLOAD_FOLDER, 'sales', str(customer.customer_id), str(login_info_id), filename])
    
    if os.path.exists(file_path):
        print "File exists"
    else:
        open(file_path, 'w')
    
    os.chmod(file_path, 0o777)
    #print file_path
    """
    doneToken = b64encode(urandom(20)).rstrip('==')
    
    
    print date
    
    username = loginInfo.username
    password = loginInfo.password
    vendor_id = loginInfo.apple_vendor_id
    #report_date_str = endDate.strftime('%Y%m%d')
    date_type='Daily'
    report_subtype='Summary'
    report_type='Sales'
    
    """
    records = []
    for delta in range((endDate - startDate).days + 1):
        reportDate = startDate + timedelta(days=delta)
        #report_date_str = reportDate.strftime('%Y%m%d')
        reportDateStr = str(reportDate)
        reportDate = parser.parse(reportDateStr).date()
        print reportDate
        #fileRecords = itunes_records(username,password,vendor_id,report_type,date_type,report_subtype,report_date_str,customerId)
        fileRecords = fetch_apple_daily_sales_report(username,password,vendor_id,reportDate)
        if fileRecords:
            records.extend(fileRecords)
    """
    #print startDate
    
    """
    # Create google_report_records table.
    schema = [
        {'name': 'customer_id', 'type': 'INTEGER', 'mode': 'required', 'description': 'Customer ID'},
        {'name': 'order_number', 'type': 'STRING', 'mode': 'required', 'description': 'Order Number'},
        {'name': 'charged_date', 'type': 'TIMESTAMP', 'mode': 'nullable', 'description': 'Human readable date in UTC (format: YYYY-MM-DD hh:mm:ss)'},
        {'name': 'charged_time', 'type': 'TIMESTAMP', 'mode': 'nullable', 'description': 'Human readable time in UTC (format: YYYY-MM-DD hh:mm:ss)'},
        {'name': 'financial_status', 'type': 'STRING', 'mode': 'nullable', 'description': 'Financial Status'},
        {'name': 'device_model', 'type': 'STRING', 'mode': 'nullable', 'description': 'Device Model'},
        {'name': 'product_title', 'type': 'STRING', 'mode': 'nullable', 'description': 'Product Title'},
        {'name': 'product_id', 'type': 'STRING', 'mode': 'nullable', 'description': 'Product Id'},
        {'name': 'product_type', 'type': 'STRING', 'mode': 'nullable', 'description': 'Product Type'},
        {'name': 'sku_id', 'type': 'STRING', 'mode': 'nullable', 'description': 'SKU ID'},
        {'name': 'sale_currency', 'type': 'STRING', 'mode': 'nullable', 'description': 'Currency of Sale'},
        {'name': 'item_price', 'type': 'FLOAT', 'mode': 'nullable', 'description': 'Item Price'},
        {'name': 'taxes', 'type': 'FLOAT', 'mode': 'nullable', 'description': 'Taxes Collected'},
        {'name': 'charged_amount', 'type': 'FLOAT', 'mode': 'nullable', 'description': 'Charged Amount'},
        {'name': 'developer_proceeds', 'type': 'FLOAT', 'mode': 'nullable', 'description': 'Developer Proceeds'},
        {'name': 'developer_proceeds_usd', 'type': 'FLOAT', 'mode': 'nullable', 'description': 'Developer Proceeds USD'},
        {'name': 'buyer_city', 'type': 'STRING', 'mode': 'nullable', 'description': 'City of Buyer'},
        {'name': 'buyer_state', 'type': 'STRING', 'mode': 'nullable', 'description': 'State of Buyer'},
        {'name': 'buyer_postal_code', 'type': 'STRING', 'mode': 'nullable', 'description': 'Postal Code of Buyer'},
        {'name': 'buyer_country', 'type': 'STRING', 'mode': 'nullable', 'description': 'Country of Buyer'},
        {'name': 'timestamp', 'type': 'INTEGER', 'mode': 'nullable', 'description': 'Unix Timestamp'},
        {'name': 'creation_time', 'type': 'TIMESTAMP', 'mode': 'nullable', 'description': 'Human readable time in UTC (format: YYYY-MM-DD hh:mm:ss)'},
        {'name': 'last_modified', 'type': 'TIMESTAMP', 'mode': 'nullable', 'description': 'Human readable time in UTC (format: YYYY-MM-DD hh:mm:ss)'}
    ]
    created = client.create_table('mobbo_dashboard', 'google_report_records', schema)
    """
    
    # Submit an async query.

    """
    job_id, _results = client.query('select * from mobbo_dashboard.names_2014 limit 10')

    # Check if the query has finished running.
    complete, row_count = client.check_job(job_id)

    # Retrieve the results.
    results = client.get_query_rows(job_id)

    for record in results:
        print record['name']
        
    #print results
    """
    return render(request, "download/test.html")


def gcloud(request):
    #credentials = GoogleCredentials.get_application_default()
    """
    tz = timezone('America/Los_Angeles')
    todayLocal = from_timestamp(utc_epoch(), tz).date()
    reportDate = todayLocal - timedelta(days=1)
    etaDate = todayLocal
    etaDatetime = datetime.combine(etaDate, _4_AM)
    etaUtc = etaDatetime.replace(tzinfo=tz).astimezone(utc)

    print etaUtc
    """
    """
    client = bigquery.Client(project='mobbo-dashboard')
    dataset = client.dataset('mobbo_dashboard')
    table = dataset.table(name='google_report_records')
    table.schema = [
                SchemaField('customer_id', 'INTEGER', mode='required'),
                SchemaField('order_number', 'STRING', mode='required'),
                SchemaField('charged_date', 'STRING', mode='nullable'),
                SchemaField('charged_time', 'STRING', mode='nullable'),
                SchemaField('financial_status', 'STRING', mode='nullable'),
                SchemaField('device_model', 'STRING', mode='nullable'),
                SchemaField('product_title', 'STRING', mode='nullable'),
                SchemaField('product_id', 'STRING', mode='nullable'),
                SchemaField('product_type', 'STRING', mode='nullable'),
                SchemaField('sku_id', 'STRING', mode='nullable'),
                SchemaField('sale_currency', 'STRING', mode='nullable'),
                SchemaField('item_price', 'FLOAT', mode='nullable'),
                SchemaField('taxes', 'FLOAT', mode='nullable'),
                SchemaField('charged_amount', 'FLOAT', mode='nullable'),
                SchemaField('developer_proceeds', 'FLOAT', mode='nullable'),
                SchemaField('developer_proceeds_usd', 'FLOAT', mode='nullable'),
                SchemaField('buyer_city', 'STRING', mode='nullable'),
                SchemaField('buyer_state', 'STRING', mode='nullable'),
                SchemaField('buyer_postal_code', 'STRING', mode='nullable'),
                SchemaField('buyer_country', 'STRING', mode='nullable'),
                SchemaField('timestamp', 'INTEGER', mode='nullable'),
                SchemaField('creation_time', 'STRING', mode='nullable'),
                SchemaField('last_modified', 'STRING', mode='nullable')
                    ]
    with open('/var/www/Projects/mobbo-dashboards2/django_project/keyset/test.csv', 'rb') as csv_file:
        reader = csv.reader(csv_file)
        rows = list(reader)
    table.insert_data(rows)
    
    """
    start_date_str = '2016-06-27'
    customer_id = 1
    login_info_id = 2
    filename = "apple_report_records_%s.csv" %(start_date_str)
    #file_path = '/'.join([settings.ITUNES_UPLOAD_FOLDER, 'sales', str(customer_id), str(login_info_id), filename])
    
    file_path = '/var/www/Projects/mobbo-dashboards2/django_project/mobbo/static/google_play/customers/sales/1/1/google_report_reports.csv'
    print file_path
    BigQuery.insertCSV(file_path,'google_report_records')
    return render(request, "download/test.html")

def appinfo(request):
    """
    url ="http://mobbo.com/Android/AppDetails/air.com.chicgames.summergirldressup"
    hdr = {'User-Agent':'Mozilla/5.0'}
    req = urllib2.Request(url,headers=hdr)
    try:
        response = urllib2.urlopen(req)
        data = simplejson.load(response)
    except urllib2.HTTPError, e:
        print e.fp.read()
    
    #print data
    """
    loginId = 1
    login = CustomerExternalLoginInfo.objects.get(pk=loginId)
    customer = login.customer_id

    todayUtc = from_timestamp(utc_epoch(), utc).date()
    yesterdayUtc = todayUtc - timedelta(days=1)
    yearmonth = datetime.now().strftime("%Y%m")

    records = fetch_google_app_packages_name(login.refresh_token, login.gc_bucket_id, yearmonth)

    print records
    sku = None
    #productId = 'com.BlackSheepGames.DoodleSanta'
    #appInfo = fetcher.ANDROID_APP_INFO_FETCHER.fetch(productId,sku,customer,login)
  
    appInfos = [ai for ai in AppInfo.objects.filter(customer_id=customer, platform='Google Play')]
    idToApp = {ai.app: ai for ai in appInfos}
    for record in records:
        productId = record
        if productId not in idToApp:
            print productId
            appInfo = fetcher.ANDROID_APP_INFO_FETCHER.fetch(productId,sku,customer,login)
    
     
    """
	outfile_path = '/var/www/Projects/mobbo-dashboards2/django_project/keyset/appinfo.csv'
	writer = csv.writer(open(outfile_path, 'w'))
	
	for record in records:
		url = _ANDROID_APP_INFO_URL % (record)
		response = requests.get(url)
		if response.status_code != 404:
			results = response.json()
			if results['name'] is not None:
                customer_id = int(customerId.customer_id)
                app=record
                name=results['name']
                identifier=''
                artist_id=''
                platform=ANDROID_PLATFORM_STRING
                platform_type_id=2
                category=results['category']
				price=results['price']
				formatted_price=''
				currency='USD'
				description=''
				icon_url=results['icon'][:-3]
				app_screenshots = results['screenshots']
				rating=results['rating']
				rating1=results['rating1']
				rating2=results['rating2']
				rating3=results['rating3']
				rating4=results['rating4']
				rating5=results['rating5']
				version=results['version']
				content_rating=results['contentRating']
				size=results['size']
				developer=''
				developer_email=results['email']
				developer_website=results['website']
				install=results['installs']
				has_iap=results['hasIAP']
				iap_min=results['IAPmin']
				iap_max=results['IAPmax']
				release_date=results['updatedTo']
				
				writer.writerow([customer_id, app, name, identifier, artist_id, platform, platform_type_id, category, price, formatted_price, currency, description, icon_url, app_screenshots, rating, 
						rating1, rating2, rating3, rating4, rating5, version, content_rating, size, developer, developer_email, developer_website, install, has_iap, iap_min, iap_max, release_date])
	
	"""					
    return render(request, "download/test.html")

def send_email_message(request):
	send_mail(
		'Subject here',
		'Here is the message.',
		'test@gmail.com',
		['prabhjotelance@gmail.com'],
		fail_silently=False,
	)
	return render(request, "download/test.html")
	
