import csv
import logging

from base64 import b64encode
from boto import connect_gs, storage_uri
from boto.exception import InvalidUriError
from core.currency import convert_decimal_to_usd
from core.db.constants import TEN_PLACES
from core.oauth import scriber_gcs_boto_plugin
from core.oauth.constants import GSUTIL_CLIENT_ID, GSUTIL_CLIENT_NOTSOSECRET
from core.timeutils import from_timestamp, utc_epoch
from datetime import date, datetime, time, timedelta
from dateutil import parser
from decimal import Decimal
from django.db import transaction
from operator import attrgetter

from metrics.models import GoogleReportRecord, GoogleInstallationReportRecord
from metrics.salesreports import ReportUnavailableException
from os import urandom
from pytz import utc
from re import match
from StringIO import StringIO
from zipfile import ZipFile
from appinfo import fetcher


_GOOGLE_REPORT_BUCKET_BASE = "gs://pubsite_prod_rev_"
_GOOGLE_INSTALLATION_REPORT_EXPECTED_FIELDS = [
  'Date',                     # 0
  'Package Name',             # 1
  'Country',             	  # 2
  'Current Device Installs',  # 3
  'Daily Device Installs',    # 4
  'Daily Device Uninstalls',  # 5
  'Daily Device Upgrades',    # 6
  'Current User Installs',    # 7
  'Total User Installs',      # 8
  'Daily User Installs',      # 9
  'Daily User Uninstalls'     # 10
]

scriber_gcs_boto_plugin.SetAuthInfo(None, GSUTIL_CLIENT_ID, GSUTIL_CLIENT_NOTSOSECRET)

logger = logging.getLogger(__name__)


class GoogleInstallationReportProcessor(object):
  def process(self, report_location, start_date, end_date, customerId):
    # Unavailable monthly report files will manifest as InvalidUriErrors.
    try:
      storageUri = storage_uri(report_location)
      storageUri.connection = connect_gs()
      report = storageUri.get_contents_as_string().decode('utf-16')
    except InvalidUriError as e:
      raise ReportUnavailableException('Report not yet available: %s' % e.message)

    reader = csv.reader(report.splitlines(), delimiter=',')
    records = []
    for i, row in enumerate(reader):
		downloadData = {}
		if i == 0:
			if _GOOGLE_INSTALLATION_REPORT_EXPECTED_FIELDS != \
				row[:len(_GOOGLE_INSTALLATION_REPORT_EXPECTED_FIELDS)]:
			  logger.warning('Encountered unexpected google report fields: %s' % row)
			  break
		else:
			recordDate = parser.parse(row[0]).date()
			record_date = datetime.combine(recordDate, time.min)
			downloadData['record_date'] = str(record_date)
			downloadData['date'] = recordDate
			
			if not(start_date <= recordDate <= end_date):
				continue
				
			downloadData['customer_id'] = int(customerId.customer_id)
			downloadData['package_name'] = row[1]
			downloadData['country'] = row[2]
			downloadData['current_device_installs'] = int(row[3])
			downloadData['daily_device_installs'] = int(row[4])
			downloadData['daily_device_uninstalls'] = int(row[5])
			downloadData['daily_device_upgrades'] = int(row[6])
			downloadData['current_user_installs'] = int(row[7])
			downloadData['total_user_installs'] = int(row[8])
			downloadData['daily_user_installs'] = int(row[9])
			downloadData['daily_user_uninstalls'] = int(row[10])
			todayUtc = datetime.now()
			downloadData['creation_time'] = str(todayUtc)
			downloadData['last_modified'] = str(todayUtc)
			
			records.append(downloadData)
			
    return records

def _report_file_names(bucket_id, start_date, end_date):
	fileNames = []
	startDateFloor = date(year=start_date.year, month=start_date.month, day=1)
	endDateFloor = date(year=end_date.year, month=end_date.month, day=1)
	bucket = storage_uri(_GOOGLE_REPORT_BUCKET_BASE + bucket_id)
	for obj in bucket.list_bucket(prefix='stats/installs/installs'):
		m = match(r'^stats/installs/(installs_[^_]+_([\d]+)_country.csv)$', obj.name)
		if m:
			# We expect YYYYMM format.
			reportDateStr = m.group(2)
			reportDateFloor = date(year=int(reportDateStr[:4]), month=int(reportDateStr[4:6]), day=1)
			if (startDateFloor <= reportDateFloor <= endDateFloor) and (start_date <= end_date):
				#print m.group(1)
				fileNames.append(m.group(1))
	return fileNames

def _report_folder(report_type):
  if report_type not in _GOOGLE_REPORT_TYPES:
    raise ValueError('Unrecognized report type %s' % report_type)
  elif report_type in ['payouts', 'sales', 'earnings']:
    return report_type
  elif report_type == 'installs':
    return 'stats/installs'
  else:
    raise NotImplementedError



def fetch_google_install_report(refresh_token, bucket_id, start_date, end_date, customerId):
	
	scriber_gcs_boto_plugin.SetAuthInfo(refresh_token)

	# The request_nonce is only used to disambiguate requests made within short times of one another.
	# Uniqueness is not required.
	request_nonce = b64encode(urandom(10)).rstrip('==')
	request_time = from_timestamp(utc_epoch(), utc)
	reportFolder = 'stats/installs'
	#install_files_location = '/'.join([_GOOGLE_REPORT_BUCKET_BASE + bucket_id, reportFolder])
	#src_uri = storage_uri(install_files_location)
	
	reportFileNames = _report_file_names(bucket_id, start_date, end_date)
	
	records = []
	for reportFileName in reportFileNames:
		reportLocation = '/'.join([_GOOGLE_REPORT_BUCKET_BASE + bucket_id, reportFolder, reportFileName])
		reportProcessor = GoogleInstallationReportProcessor()
		fileRecords = reportProcessor.process(reportLocation, start_date, end_date, customerId)
		if fileRecords:
			records.extend(fileRecords)
	
	return records

def retrieve_from_db(ordernumber,financialStatus):
	try:
		reportInfo = GoogleReportRecord.objects.filter(order_number=ordernumber,financial_status=financialStatus)
		return reportInfo
	except GoogleReportRecord.DoesNotExist:
		return None


def retrieve_install_record(country,date,package_name):
	try:
		reportInfo = GoogleInstallationReportRecord.objects.filter(date=date, country=country, package_name = package_name)
		return reportInfo
	except GoogleInstallationReportRecord.DoesNotExist:
		return None


def fetch_google_app_packages_name(refresh_token, bucket_id, yearmonth):
	
	scriber_gcs_boto_plugin.SetAuthInfo(refresh_token)
	reportFolder = _report_folder('installs')
	
	packages = []
	bucket = storage_uri(_GOOGLE_REPORT_BUCKET_BASE + bucket_id)
	for obj in bucket.list_bucket(prefix='stats/installs/installs_'):
		m = match(r'^stats/installs/(installs_([^_]+)_([\d]+)_country.csv)$', obj.name)
		if m:
			# get app package name
			appname = m.group(2)
			if appname not in packages:
				packages.append(appname)
			
	return packages
