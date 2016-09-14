from __future__ import absolute_import
import logging
import json
import requests
import csv
import os
import traceback
import urllib2
import time as TI
from appinfo import fetcher
from celery import chain, chord, group, task
from celery.utils.log import get_task_logger
from core.celeryutils import exponential_backoff
from core.db.constants import TEN_PLACES
from core.timeutils import from_timestamp, utc_epoch, DATE_FMT
from core.utils import unpack
from customers.models import Customer, CustomerExternalLoginInfo
from datetime import date, datetime, time, timedelta
from dateutil import parser
from decimal import Decimal
from django.core.cache import cache
from django.db import connection, IntegrityError, transaction
from django.db.models import Q
from appinfo.models import AppInfo
#from ingestor.models import App, Channel, ChannelProduct, PlatformApp, PlatformType, Product
#from metrics.constants import APPLE_REPORT_TERRITORY_TIMEZONES
from metrics.googlesalesreports import fetch_google_daily_sales_report, fetch_google_report
from metrics.googleinstallreports import fetch_google_install_report
#from metrics.models import DailyReportAvailabilityTime, DailySalesReportMetrics
from metrics.salesreports import fetch_apple_daily_sales_report, ReportUnavailableException
from metrics.models import GoogleReportRecord
#from ml.modelregistry import DAILY_REVENUE
#from ml.tasks import train_model
from customers import bigquery
from pytz import timezone, utc
from re import match
from django.conf import settings
from download.big_query import BigQuery

GOOGLE_CLOUD = CustomerExternalLoginInfo.GOOGLE_CLOUD
ITUNES_CONNECT = CustomerExternalLoginInfo.ITUNES_CONNECT

# The maximum number of times a task from this module may be retried.
_MAX_RETRIES = 7

# Probe daily reports status using login information under only our control.
_POLLING_BUCKET_ID = '00292849710855110990'
_POLLING_USERNAME = 'dan@scriber.io'

_DEFAULT_CURRENCY = 'USD'
_CURRENCT_CONVERTER_URL = 'http://currencies.apps.grandtrunk.net/getrate'

# Time constants used for report polling.
_4_AM = time(4, 0)
_6_AM = time(6, 0)
_10_PM = time(22, 0)
_10_MINUTES_SECS = 600
_30_MINUTES_SECS = 1800

logger = get_task_logger(__name__)

class ReportFetchExhaustionException(Exception):
  pass

def kickoff_retry_countdown(timezone):
  currentTime = from_timestamp(utc_epoch(), timezone).time()
  if currentTime <= _6_AM:
    return _10_MINUTES_SECS
  elif currentTime <= _10_PM:
    return _30_MINUTES_SECS
  else:
    return None

# TODO(d-felix): Merge this task and the territory task since we now plan to use different
# celery beat entries for different territories.
@task(max_retries=_MAX_RETRIES, ignore_result=True, bind=True)
def daily_apple_metrics_kickoff(self, *args, **kwargs):
	try:
		(tzStr, ) = unpack(kwargs, 'timezone_str')
		tz = timezone(tzStr)
		
		todayLocal = from_timestamp(utc_epoch(), tz).date()
		yesterdayLocal = todayLocal - timedelta(days=1)
		endDate = yesterdayLocal
		
		logins = CustomerExternalLoginInfo.objects.filter(external_service=ITUNES_CONNECT,
			apple_vendor_id__isnull=False, is_active=True)
		
		taskList = []
		for login in logins:
			customer = login.customer_id
			date = bigquery.apple_latest_record(customer.customer_id,login.login_info_id)
			startDate = date + timedelta(days=1)
			start_date = str(startDate)
			end_date = str(endDate)
			
			taskList.append(batch_daily_apple_metrics.s(login_id=login.login_info_id,
				start_date_str=start_date, end_date_str=end_date))
		
		reportTaskGroup = group(taskList)
		reportTaskGroup.apply_async()

		#kwargs = {'report_date_str': str(reportDate), 'timezone_str': tzStr}
		#daily_apple_metrics_territory_kickoff.apply_async(None, kwargs, eta=etaUtc)

	except Exception as e:
		raise self.retry(exc=e, countdown=_10_MINUTES_SECS)

@task(max_retries=None, ignore_result=True, bind=True)
def daily_apple_metrics_territory_kickoff(self, *args, **kwargs):
  try:
    reportDateStr, timezoneStr = unpack(kwargs, 'report_date_str', 'timezone_str')

    # For now, silently succeed for non-US territories.
    if timezoneStr != 'America/Los_Angeles':
      return

    # parser.parse() returns a datetime.datetime object.
    reportDate = parser.parse(reportDateStr).date()

    # TODO(d-felix): When necessary, establish canonical logins for non-US territories.
    pollingLogin = CustomerExternalLoginInfo.objects.filter(
        customer_id__auth_user__username=_POLLING_USERNAME,
        external_service=CustomerExternalLoginInfo.ITUNES_CONNECT, is_active=True).first()
    pollingTimezone = timezone(pollingLogin.customer_id.timezone)

    # Raises a ReportUnavailableException if reports are not ready.
    report = fetch_apple_daily_sales_report(pollingLogin.username, pollingLogin.password,
        pollingLogin.apple_vendor_id, reportDate)

    # TODO(d-felix): Filter by relevent territory.
    logins = CustomerExternalLoginInfo.objects.filter(external_service=ITUNES_CONNECT,
        is_active=True)
    taskList = []
    for login in logins:
      taskList.append(daily_apple_metrics.s(login_id=login.login_info_id,
          report_date_str=reportDateStr))
    reportTaskGroup = group(taskList)
    reportTaskGroup.apply_async()

    # Record the availability time.
    utcNow = from_timestamp(utc_epoch(), utc)
    availTime = DailyReportAvailabilityTime(external_service=ITUNES_CONNECT, report_type='Sales',
        report_region=timezoneStr, report_date=reportDate, time=utcNow)
    try:
      availTime.save()
    except IntegrityError as e:
      logger.warning('Could not record apple sales report availability due to IntegrityError: %s'
          % e.message)

  except Exception as e:
    if 'pollingTimezone' in locals():
      tz = pollingTimezone
    else:
      logger.info('Could not identify time zone corresponding to auth user %s' %
          _POLLING_USERNAME)
      tz = timezone('America/Los_Angeles')
    retryCountdown = kickoff_retry_countdown(tz)
    if retryCountdown is None:
      raise ReportFetchExhaustionException(
          'Abandoning daily apple report fetching due to too many failures')
    else:
      raise self.retry(exc=e, countdown=retryCountdown)

@task(max_retries=_MAX_RETRIES, ignore_result=True, bind=True)
def batch_daily_apple_metrics(self, *args, **kwargs):
    try:
        loginId, startDateStr, endDateStr, doneToken = unpack(kwargs, 'login_id', 'start_date_str',
            'end_date_str', 'done_token')
        # parser.parse() returns a datetime.datetime object.
        startDate = parser.parse(startDateStr).date()
        endDate = parser.parse(endDateStr).date()
        taskList = []
        for delta in range((endDate - startDate).days + 1):
            reportDate = startDate + timedelta(days=delta)
            if doneToken:
                taskList.append(daily_apple_metrics_store_result.s(login_id=loginId,
                    report_date_str=str(reportDate), done_token = doneToken))
            else:
                taskList.append(daily_apple_metrics.s(login_id=loginId, report_date_str=str(reportDate), done_token = doneToken))
        """
        if doneToken:
            callback = import_itunes_csv.s(done_token=doneToken, login_id=loginId)
            batchTasks = chord(taskList, callback)
        else:
            batchTasks = group(taskList)
        """
        batchTasks = group(taskList)
        batchTasks.apply_async()
        #batchTasks.apply()
    
    except Exception as e:
        # Treat all exceptions as transient errors and retry.
        raise self.retry(exc=e, countdown=exponential_backoff(self.request.retries))


@task(max_retries=_MAX_RETRIES, ignore_result=True, bind=True)
def daily_apple_metrics(self, *args, **kwargs):
  try:
    return daily_apple_metrics_inner_function(*args, **kwargs)
  except Exception as e:
    # Treat all exceptions as transient errors and retry.
    raise self.retry(exc=e, countdown=exponential_backoff(self.request.retries))

@task(max_retries=_MAX_RETRIES, ignore_result=False, bind=True)
def daily_apple_metrics_store_result(self, *args, **kwargs):
  try:
    return daily_apple_metrics_inner_function(*args, **kwargs)
  except Exception as e:
    # Treat all exceptions as transient errors and retry.
    raise self.retry(exc=e, countdown=exponential_backoff(self.request.retries))

def daily_apple_metrics_inner_function(*args, **kwargs):
    loginId, reportDateStr, doneToken = unpack(kwargs, 'login_id', 'report_date_str', 'done_token')
    login = CustomerExternalLoginInfo.objects.get(pk=loginId)
    customer = login.customer_id
    tz = timezone(customer.timezone)
   
    if reportDateStr is None:
        reportDate = from_timestamp(utc_epoch(), tz).date() - timedelta(days=1)
    else:
        # parser.parse() returns a datetime.datetime object.
        reportDate = parser.parse(reportDateStr).date()
    
    records = fetch_apple_daily_sales_report(login.username, login.password,
        login.apple_vendor_id, reportDate)

    # Create csv file
    filename = "apple_report_records_%s.csv" %(reportDateStr)
    folder = '/'.join([settings.ITUNES_UPLOAD_FOLDER, 'sales', str(customer.customer_id), str(loginId)])
    file_path = '/'.join([settings.ITUNES_UPLOAD_FOLDER, 'sales', str(customer.customer_id), str(loginId), filename])
    
    if not os.path.exists(folder):
        os.makedirs(folder) 
    
    """
    if os.path.isfile(file_path+'/apple_report_reports.csv'):
        os.remove(file_path+'/apple_report_reports.csv')
    """
    """
    if os.path.isfile(file_path+'/apple_report_reports.csv'):
        writer = csv.writer(open(file_path+'/apple_report_reports.csv', 'a'))
    else:
        writer = csv.writer(open(file_path+'/apple_report_reports.csv', 'w'))
    """
    fSubset = open(file_path, 'w')
    os.chmod(file_path, 0o777)
    #TI.sleep(10)
    
    writer = csv.writer(fSubset)
    packageList = []
    for rec in records:
        if doneToken:
            package = rec['apple_identifier']
            sku = rec['sku']
            if package not in packageList:
                fetcher.IOS_ID_APP_INFO_FETCHER.fetch(package,sku,customer,login)
                packageList.append(package)
        
        writer.writerow([customer.customer_id, loginId, rec['apple_identifier'], rec['provider'], rec['provider_country'], rec['sku'], rec['developer'] ,rec['title'], rec['version'], rec['product_type_identifier'],
            rec['units'], rec['developer_proceeds'], rec['developer_proceeds_usd'], rec['begin_date'], rec['end_date'], rec['customer_currency'], rec['country_code'], rec['currency_of_proceeds'], rec['customer_price'],
            rec['promo_code'], rec['parent_identifier'], rec['subscription'], rec['period'], rec['category'],rec['cmb'],rec['device'],rec['supported_platforms']])
    
    fSubset.close()
    
    # Import Csv File
    if os.path.isfile(file_path):
        logger.info('import csv file in bigquery %s' % file_path)
        BigQuery.insert_itunesCSV(file_path,'apple_report_records')	
    
    """
    # Produce dicts of known apple identifiers and bundle IDs.
    # These dicts are updated as new database entities are saved.
    appInfos = [ai for ai in AppInfo.objects.filter(customer_id=customer, platform='App Store')]
    identifierToProduct = {ai.identifier: ai for ai in appInfos}
    for record in records:
        identifier = record.apple_identifier
        if identifier not in identifierToProduct:
            appInfo = fetcher.IOS_ID_APP_INFO_FETCHER.fetch(identifier, customer)
            if appInfo is None:
                logger.warning('Could not retrieve app info for apple identifier %s' % identifier)
                continue
    """

@task(max_retries=_MAX_RETRIES, ignore_result=True, bind=True)
def import_itunes_csv(self, *args, **kwargs):
  try:
    loginId, reportDateStr = unpack(kwargs, 'login_id', 'report_date_str')
    login = CustomerExternalLoginInfo.objects.get(pk=loginId)
    customer = login.customer_id
    tz = timezone(customer.timezone)

    if reportDateStr is None:
        reportDate = from_timestamp(utc_epoch(), tz).date() - timedelta(days=1)
    else:
        # parser.parse() returns a datetime.datetime object.
        reportDate = parser.parse(reportDateStr).date()

    # Create csv file
    filename = "apple_report_records_%s.csv" %(reportDateStr)
    folder = '/'.join([settings.ITUNES_UPLOAD_FOLDER, 'sales', str(customer.customer_id), str(loginId)])
    file_path = '/'.join([settings.ITUNES_UPLOAD_FOLDER, 'sales', str(customer.customer_id), str(loginId), filename])

    # Import Csv File
    if os.path.isfile(file_path):
        os.chmod(file_path, 0o777)
        logger.info('import csv file in bigquery %s' % file_path)
        BigQuery.insert_itunesCSV(file_path,'apple_report_reports')

    # Import Csv File
    #BigQuery.insertCSV(file_path+'/apple_report_reports.csv','apple_report_reports')

  except Exception as e:
    raise self.retry(exc=e, countdown=exponential_backoff(self.request.retries))


def import_csv(*args, **kwargs):
	loginId, reportDateStr = unpack(kwargs, 'login_id', 'report_date_str')
	login = CustomerExternalLoginInfo.objects.get(pk=loginId)
	customer = login.customer_id
	tz = timezone(customer.timezone)
   
	if reportDateStr is None:
		reportDate = from_timestamp(utc_epoch(), tz).date() - timedelta(days=1)
	else:
		# parser.parse() returns a datetime.datetime object.
		reportDate = parser.parse(reportDateStr).date()
	
	# Create csv file
	filename = "apple_report_records_%s.csv" %(reportDateStr)
	folder = '/'.join([settings.ITUNES_UPLOAD_FOLDER, 'sales', str(customer.customer_id), str(loginId)])
	file_path = '/'.join([settings.ITUNES_UPLOAD_FOLDER, 'sales', str(customer.customer_id), str(loginId), filename])
	
	# Import Csv File
	if os.path.isfile(file_path):
		logger.info('import csv file in bigquery %s' % file_path)
		BigQuery.insertCSV(file_path,'apple_report_reports')

# TODO(d-felix) Improve the retry schedule once we have sufficient data.
@task(max_retries=48, ignore_result=True, bind=True)
def daily_google_metrics_kickoff(self, *args, **kwargs):
	try:
		(tzStr, ) = unpack(kwargs, 'timezone_str')
		tz = timezone(tzStr)
		
		todayLocal = from_timestamp(utc_epoch(), tz).date()
		yesterdayLocal = todayLocal - timedelta(days=1)
		endDate = yesterdayLocal
		
		logins = CustomerExternalLoginInfo.objects.filter(external_service=GOOGLE_CLOUD,
			refresh_token__isnull=False, is_active=True)
		
		taskList = []
		for login in logins:
			customer = login.customer_id
			salesDate = bigquery.google_sales_latest_record(customer.customer_id,login.login_info_id)
			downloadDate = bigquery.google_download_latest_record(customer.customer_id,login.login_info_id)
			
			sales_startDate = salesDate + timedelta(days=1)
			download_startDate = downloadDate + timedelta(days=1)
			
			sales_start_date = str(sales_startDate)
			download_start_date = str(download_startDate)
			end_date = str(endDate)
			
			taskList.append(batch_daily_google_metrics.s(login_id=login.login_info_id,
				sales_start_date_str=sales_start_date, download_start_date_str=download_start_date, end_date_str=end_date))
				
		reportTaskGroup = group(taskList)
		reportTaskGroup.apply_async()

	except Exception as e:
		raise self.retry(exc=e, countdown=_30_MINUTES_SECS)


@task(max_retries=_MAX_RETRIES, ignore_result=True, bind=True)
def batch_daily_google_metrics(self, *args, **kwargs):
  try:
    batch_tasks = chain(
        batch_daily_google_sales_metrics.s(**kwargs),
        batch_daily_import_sales_csv_metrics.s(**kwargs),
        batch_daily_google_package_installation_metrics.s(**kwargs)
        )
 
    batch_tasks.apply_async()
    
  except Exception as e:
    # Treat all exceptions as transient errors and retry.
    raise self.retry(exc=e, countdown=exponential_backoff(self.request.retries))


@task(max_retries=_MAX_RETRIES, ignore_result=True, bind=True)
def batch_daily_import_sales_csv_metrics(self, *args, **kwargs):
  try:
    loginInfoId, startDateStr, endDateStr, doneToken = unpack(kwargs, 'login_id',
        'sales_start_date_str', 'end_date_str', 'done_token')
    login = CustomerExternalLoginInfo.objects.get(pk=loginInfoId)
    customer = login.customer_id
    
    # import sales csv file in bigquery
    filename = "google_report_records.csv"
    file_path = '/'.join([settings.GOOGLE_PLAY_UPLOAD_FOLDER, 'sales', str(customer.customer_id), str(loginInfoId), filename])
    #BigQuery.insertCSV(file_path+'/google_report_reports.csv','google_report_records')
    if os.path.isfile(file_path):
        BigQuery.insertCSV(file_path,'google_report_records')
 
   
  except Exception as e:
    logger.info(traceback.format_exc())
    # Treat all exceptions as transient errors and retry.
    raise self.retry(exc=e, countdown=exponential_backoff(self.request.retries))


@task(max_retries=_MAX_RETRIES, ignore_result=True, bind=True)
def batch_daily_import_install_csv_metrics(self, *args, **kwargs):
  try:
    loginInfoId, startDateStr, endDateStr, doneToken = unpack(kwargs, 'login_info_id',
        'start_date_str', 'end_date_str', 'done_token')
    login = CustomerExternalLoginInfo.objects.get(pk=loginInfoId)
    customer = login.customer_id
    
    # import sales csv file in bigquery
    filename = "google_report_reports.csv"
    file_path = '/'.join([settings.GOOGLE_PLAY_UPLOAD_FOLDER, 'sales', str(customer.customer_id), str(loginInfoId), filename])
    
    if os.path.isfile(file_path):
		BigQuery.insertCSV(file_path,'google_installation_report_records')
 
   
  except Exception as e:
    logger.info(traceback.format_exc())
    # Treat all exceptions as transient errors and retry.
    raise self.retry(exc=e, countdown=exponential_backoff(self.request.retries))


@task(max_retries=_MAX_RETRIES, ignore_result=True, bind=True)
def batch_daily_google_sales_metrics(self, *args, **kwargs):
  try:
    loginInfoId, startDateStr, endDateStr, doneToken = unpack(kwargs, 'login_id',
        'sales_start_date_str', 'end_date_str', 'done_token')
    login = CustomerExternalLoginInfo.objects.get(pk=loginInfoId)
    customer = login.customer_id
    
    if not (startDateStr and endDateStr):
      raise ValueError('Missing or invalid arguments start_date_str: %s and end_date_str: %s' %
          (startDateStr, endDateStr))
    startDate = parser.parse(startDateStr).date()
    endDate = parser.parse(endDateStr).date()

    records = fetch_google_report(login.refresh_token, login.gc_bucket_id, 'sales',
        startDate, endDate, customer, app_id=None)

    # fetch_google_daily_sales_report may succeed without returning any records.
    # This can happen if the monthly report zip file is available for download,
    # but no records matching the provided reportDate are found.
    if not records:
        logger.info('Google report fetch succeeded but no records were returned from %s to %s' %
            (startDateStr, endDateStr))
        return
      #raise ReportUnavailableException(
          #'Google report fetch succeeded but no records were returned.')
    
  
    # Create csv file
    filename = "google_report_records.csv"
    folder = '/'.join([settings.GOOGLE_PLAY_UPLOAD_FOLDER, 'sales', str(customer.customer_id), str(loginInfoId)])
    file_path = '/'.join([settings.GOOGLE_PLAY_UPLOAD_FOLDER, 'sales', str(customer.customer_id), str(loginInfoId), filename])
  
    if not os.path.exists(folder):
        os.makedirs(folder) 
    
    if os.path.isfile(file_path):
        os.remove(file_path)
    
    fSubset = open(file_path, 'w')
    os.chmod(file_path, 0o777)    
    writer = csv.writer(open(file_path, 'w'))
    for rec in records:
        writer.writerow([rec['customer_id'], loginInfoId, rec['order_number'], rec['charged_date'], rec['charged_time'], rec['financial_status'], rec['device_model'] ,rec['product_title'], rec['product_id'], rec['product_type'],
                        rec['sku_id'], rec['sale_currency'], rec['item_price'], rec['taxes'], rec['charged_amount'], rec['developer_proceeds'], rec['developer_proceeds_usd'], rec['buyer_city'], rec['buyer_state'],
                        rec['buyer_postal_code'], rec['buyer_country'], rec['timestamp'], rec['creation_time'], rec['last_modified']])
    
    
    fSubset.close()
    
  except Exception as e:
    logger.info(traceback.format_exc())
    # Treat all exceptions as transient errors and retry.
    raise self.retry(exc=e, countdown=exponential_backoff(self.request.retries))


@task(max_retries=_MAX_RETRIES, ignore_result=True, bind=True)
def batch_daily_google_package_installation_metrics(self, *args, **kwargs):
  try:
    loginInfoId, startDateStr, endDateStr, doneToken = unpack(kwargs, 'login_id',
        'download_start_date_str', 'end_date_str', 'done_token')
    login = CustomerExternalLoginInfo.objects.get(pk=loginInfoId)
    customer = login.customer_id
    if doneToken:
        batch_daily_google_installation_metrics.delay(login_id=loginInfoId, start_date_str=startDateStr,
            end_date_str=endDateStr, package=None, done_token=doneToken)
    else:
        apps = bigquery.get_customer_google_app(customer.customer_id,loginInfoId)
        taskList = []
        for app in apps:
            taskList.append(batch_daily_google_installation_metrics.s(login_id=loginInfoId,
                    start_date_str=startDateStr, end_date_str=endDateStr,package=app,done_token=doneToken))
        
        reportTaskGroup = group(taskList)
        reportTaskGroup.apply_async()
  except Exception as e:
    # Treat all exceptions as transient errors and retry.
    raise self.retry(exc=e, countdown=exponential_backoff(self.request.retries))


@task(max_retries=_MAX_RETRIES, ignore_result=True, bind=True)
def batch_daily_google_app_list(self, *args, **kwargs):
  try:
    loginId, startDateStr, endDateStr, doneToken = unpack(kwargs, 'login_id',
        'start_date_str', 'end_date_str', 'done_token')
    login = CustomerExternalLoginInfo.objects.get(pk=loginId)
    customer = login.customer_id
    
    apps = bigquery.get_customer_google_app(customer.customer_id,loginId)
    if doneToken:
        for app in apps:
            fetcher.ANDROID_APP_INFO_FETCHER.fetch(app,customer,login)
    else:
        appInfos = [ai for ai in AppInfo.objects.filter(customer_id=customer, customer_account_id=loginId, platform='Google Play')]
        # Produce dicts of known packages and product IDs.
        idToApp = {ai.app: ai for ai in appInfos}
        # Create any unrecognized apps and their corresponding products.
        for app in apps:
            if app not in idToApp:
                fetcher.ANDROID_APP_INFO_FETCHER.fetch(app,customer,login)
  except Exception as e:
    # Treat all exceptions as transient errors and retry.
    raise self.retry(exc=e, countdown=exponential_backoff(self.request.retries))



@task(max_retries=_MAX_RETRIES, ignore_result=True, bind=True)
def batch_daily_google_installation_metrics(self, *args, **kwargs):
  try:
    loginId, startDateStr, endDateStr, app, doneToken = unpack(kwargs, 'login_id',
        'start_date_str', 'end_date_str', 'package', 'done_token')
    login = CustomerExternalLoginInfo.objects.get(pk=loginId)
    customer = login.customer_id
   
    if not (startDateStr and endDateStr):
      raise ValueError('Missing or invalid arguments start_date_str: %s and end_date_str: %s' %
          (startDateStr, endDateStr))
    startDate = parser.parse(startDateStr).date()
    endDate = parser.parse(endDateStr).date()
    
    records = fetch_google_report(login.refresh_token, login.gc_bucket_id, 'installs',
        startDate, endDate, customer, app_id=app)
        
    # fetch_google_daily_sales_report may succeed without returning any records.
    # This can happen if the monthly report zip file is available for download,
    # but no records matching the provided reportDate are found.
    if not records:
		logger.info('Google download report fetch succeeded but no records were returned from %s to %s' %
            (startDateStr, endDateStr))
		return
      #raise ReportUnavailableException(
          #'Google report fetch succeeded but no records were returned.')
     
    # Create csv file
    if doneToken:
        filename = "google_installation_report.csv"
    else:
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
    
    packagelist = []
    sku=None
    for rec in records:
        if doneToken:
            package = rec['package_name']
            if package not in packagelist:
                fetcher.ANDROID_APP_INFO_FETCHER.fetch(package,sku,customer,login)
                packagelist.append(package)
                
        writer.writerow([rec['customer_id'], loginId, rec['record_date'], rec['package_name'], rec['country'], rec['current_device_installs'], rec['daily_device_installs'] ,rec['daily_device_uninstalls'], 
                        rec['daily_device_upgrades'], rec['current_user_installs'], rec['total_user_installs'], rec['daily_user_installs'], rec['daily_user_uninstalls'], rec['creation_time'],
                        rec['last_modified']])
    fSubset.close()
    
    # Import Csv File
    if os.path.isfile(file_path):
        os.chmod(file_path, 0o777)
        logger.info('import install csv file in bigquery %s' % file_path)
        BigQuery.insert_googleinstallCSV(file_path,'google_installation_report_records')
    
    if doneToken:
      cache.set(doneToken, True, 60*60)
    

  except Exception as e:
    # Treat all exceptions as transient errors and retry.
    raise self.retry(exc=e, countdown=exponential_backoff(self.request.retries))



@task(max_retries=_MAX_RETRIES, ignore_result=True, bind=True)
def backfill_daily_sales_report_metrics(self, *args, **kwargs):
  try:
    loginInfoId, doneToken = unpack(kwargs, 'login_info_id', 'done_token')
    loginInfo = CustomerExternalLoginInfo.objects.get(pk=loginInfoId)
    if loginInfo.external_service == CustomerExternalLoginInfo.GOOGLE_CLOUD:
      backfill_daily_google_metrics.delay(login_info_id=loginInfoId, done_token=doneToken)
    elif loginInfo.external_service == CustomerExternalLoginInfo.ITUNES_CONNECT:
      backfill_daily_apple_metrics.delay(login_info_id=loginInfoId, done_token=doneToken)
    else:
      logger.info('Not backfilling daily sales report metrics for unrecognized service %s' %
          loginInfo.external_service)
      return
  except Exception as e:
    raise self.retry(exc=e, countdown=exponential_backoff(self.request.retries))


@task(max_retries=_MAX_RETRIES, ignore_result=True, bind=True)
def backfill_daily_apple_metrics(self, *args, **kwargs):
  try:
    loginInfoId, doneToken = unpack(kwargs, 'login_info_id', 'done_token')

    # For now assume all new customers belong to Apple's North American territory.
    #tz = timezone('America/Los_Angeles')
    #todayLocal = from_timestamp(utc_epoch(), tz).date()
    todayLocal = from_timestamp(utc_epoch(), utc).date()
    yesterdayLocal = todayLocal - timedelta(days=2)
    startDate = todayLocal - timedelta(days=30)

    # Yesterday's report may not be available yet. This can be a problem when
    # we're waiting eagerly for notification that the backfill task has
    # completed. To avoid delays, we schedule the task that pulls yesterday's
    # data separately.
    if doneToken:
      endDate = yesterdayLocal - timedelta(days=1)
      batch_daily_apple_metrics.delay(login_id=loginInfoId, start_date_str=str(startDate),
          end_date_str=str(endDate), done_token=doneToken)
      #daily_apple_metrics.delay(login_id=loginInfoId, report_date_str=str(yesterdayLocal))
    else:
      endDate = yesterdayLocal
      batch_daily_apple_metrics.delay(login_id=loginInfoId, start_date_str=str(startDate),
          end_date_str=str(endDate))

  except Exception as e:
    raise self.retry(exc=e, countdown=exponential_backoff(self.request.retries))


@task(max_retries=_MAX_RETRIES, ignore_result=True, bind=True)
def backfill_daily_google_metrics(self, *args, **kwargs):
  try:
    loginInfoId, doneToken = unpack(kwargs, 'login_info_id', 'done_token')
    loginInfo = CustomerExternalLoginInfo.objects.get(pk=loginInfoId)

    # Google reports use UTC day boundaries.
    todayUtc = from_timestamp(utc_epoch(), utc).date()
    yesterdayUtc = todayUtc - timedelta(days=1)
    startDate = todayUtc - timedelta(days=30)
    
    # Yesterday's report may not be available yet. This can be a problem when
    # we're waiting eagerly for notification that the backfill task has
    # completed. To avoid delays, we schedule the task that pulls yesterday's
    # data separately.
    if doneToken:
      endDate = yesterdayUtc - timedelta(days=1)
      batch_daily_google_metrics.delay(login_id=loginInfoId, sales_start_date_str=str(startDate),
          download_start_date_str=str(startDate), end_date_str=str(endDate), done_token=doneToken)
      #batch_daily_google_metrics.delay(login_info_id=loginInfoId, start_date_str=str(yesterdayUtc),
          #end_date_str=str(yesterdayUtc))
    else:
      endDate = yesterdayUtc
      batch_daily_google_metrics.delay(login_id=loginInfoId, sales_start_date_str=str(startDate),
          download_start_date_str=str(startDate), end_date_str=str(endDate))

  except Exception as e:
    raise self.retry(exc=e, countdown=exponential_backoff(self.request.retries))


TRAIN_MODEL_QUERY = """
  SELECT DISTINCT
    ap.id platform_id,
    c.alpha2 country_alpha2,
    cg.id category_id,
    cu.customer_id customer_id,
    cu.training_privacy training_privacy
  FROM
    customer_external_login_info li
  JOIN customers cu ON (li.customer_id = cu.customer_id)
  JOIN channel_products cp ON (li.customer_id = cp.customer_id)
  JOIN app_store_apps a ON (cp.apple_identifier = a.track_id)
  JOIN app_store_ranks k ON (k.app = a.id)
  JOIN app_store_rank_requests r ON (k.rank_request = r.id)
  JOIN app_store_categories cg ON (r.category = cg.id)
  JOIN app_store_regions rg ON (r.region = rg.id)
  JOIN countries c ON (rg.country = c.id)
  JOIN app_store_rank_types t ON (r.rank_type = t.id)
  JOIN app_store_platforms ap ON (a.platform = ap.id)
  WHERE
    li.login_info_id = %s AND
    cp.apple_identifier IS NOT NULL AND
    ap.name = 'iOS'
  ;
  """

@task(max_retries=_MAX_RETRIES, ignore_result=True, bind=True)
def all_done(self, *args, **kwargs):
  try:
    doneToken, loginId = unpack(kwargs, 'done_token', 'login_id')
    cache.set(doneToken, True, 60*60)

    taskList = []
    taskList.append(fetch_app_info.s(login_info_id=loginId))

    cursor = connection.cursor()
    cursor.execute(TRAIN_MODEL_QUERY, [loginId])
    for row in cursor.fetchall():
      platform_id, country_alpha2, category_id, customer_id, training_privacy = row[:5]
      ownerId = customer_id if training_privacy == Customer.PRIVATE else None
      taskList.append(train_model.s(model_name=DAILY_REVENUE, owner_id=ownerId, request_data=
        [{
          'platform_id': platform_id,
          'country_alpha2': country_alpha2,
          'category_id': category_id,
        }]))

    trainModelTaskGroup = group(taskList)
    trainModelTaskGroup.apply_async()

  except Exception as e:
    raise self.retry(exc=e, countdown=exponential_backoff(self.request.retries))


@task(max_retries=_MAX_RETRIES, ignore_result=True, bind=True)
def fetch_app_info(self, *args, **kwargs):
  try:
    (loginInfoId, ) = unpack(kwargs, 'login_info_id')

    taskList = []
    channelProducts = ChannelProduct.objects.filter(customer_id__auth_user__id=loginInfoId,
        platform_app_id__isnull=False)
    for cp in channelProducts:
      platformStr = cp.platform_app_id.platform_type_id.platform_type_str
      if platformStr == 'Android':
        fetcherPlatformStr = fetcher.ANDROID_PLATFORM_STRING
      elif platformStr == 'iOS':
        fetcherPlatformStr = fetcher.IOS_PLATFORM_STRING
      else:
        continue
      taskList.append(fetch_single_app_info.s(app=cp.channel_product_str,
          platform=fetcherPlatformStr))

    fetchSingleAppInfoTaskGroup = group(taskList)
    fetchSingleAppInfoTaskGroup.apply_async()

  except Exception as e:
    raise self.retry(exc=e, countdown=exponential_backoff(self.request.retries))


@task(max_retries=_MAX_RETRIES, ignore_result=True, bind=True)
def fetch_single_app_info(self, *args, **kwargs):
  try:
    app, platform = unpack(kwargs, 'app', 'platform')
    fetcher.fetch(app, platform, direct=True)

  except Exception as e:
    raise self.retry(exc=e, countdown=exponential_backoff(self.request.retries))
