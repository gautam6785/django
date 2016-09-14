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

_GOOGLE_DEVELOPER_REVENUE_SHARE = Decimal('0.7')
_GOOGLE_FEE = Decimal('0.3')
_GOOGLE_REPORT_BUCKET_BASE = "gs://pubsite_prod_rev_"
_GOOGLE_REPORT_TYPES = ['earnings', 'installs', 'payouts', 'sales']
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
_GOOGLE_EARNING_REPORT_EXPECTED_FIELDS = [
  'Description',                 #  0
  'Transaction Date',            #  1
  'Transaction Time',            #  2
  'Tax Type',                    #  3
  'Transaction Type',            #  4
  'Refund Type',                 #  5
  'Product Title',               #  6
  'Product id',                  #  7
  'Product Type',                #  8
  'Sku Id',                      #  9
  'Hardware',                    # 10
  'Buyer Country',               # 11
  'Buyer State',                 # 12
  'Buyer Postal Code',           # 13
  'Buyer Currency',              # 14
  'Amount (Buyer Currency)',     # 15
  'Currency Conversion Rate',    # 16
  'Merchant Currency',           # 17
  'Amount (Merchant Currency)',  # 18
]
_GOOGLE_SALES_REPORT_EXPECTED_FIELDS = [
  'Order Number',             #  0
  'Order Charged Date',       #  1
  'Order Charged Timestamp',  #  2
  'Financial Status',         #  3
  'Device Model',             #  4
  'Product Title',            #  5
  'Product ID',               #  6
  'Product Type',             #  7
  'SKU ID',                   #  8
  'Currency of Sale',         #  9
  'Item Price',               # 10
  'Taxes Collected',          # 11
  'Charged Amount',           # 12
  'City of Buyer',            # 13
  'State of Buyer',           # 14
  'Postal Code of Buyer',     # 15
  'Country of Buyer',         # 16
]

scriber_gcs_boto_plugin.SetAuthInfo(None, GSUTIL_CLIENT_ID, GSUTIL_CLIENT_NOTSOSECRET)

logger = logging.getLogger(__name__)

class GoogleSalesReportProcessor(object):
  def process(self, report_location, start_date, end_date, customerId):
    compressedData = StringIO()

    # Unavailable monthly report files will manifest as InvalidUriErrors.
    try:
      storageUri = storage_uri(report_location)
      storageUri.connection = connect_gs()
      storageUri.get_contents_to_stream(compressedData)
    except InvalidUriError as e:
      raise ReportUnavailableException('Report not yet available: %s' % e.message)

    zipData = ZipFile(compressedData)

    # We expect exactly one file in the archive.
    zipFilename = zipData.namelist()[0]
    salesReportFile = zipData.open(zipFilename)
    reader = csv.reader(salesReportFile.readlines(), delimiter=',')
    records = []
    for i, row in enumerate(reader):
      salesData = {}		
      if i == 0:
        if _GOOGLE_SALES_REPORT_EXPECTED_FIELDS != row[:len(_GOOGLE_SALES_REPORT_EXPECTED_FIELDS)]:
          logger.warning('Encountered unexpected google report fields: %s' % row)
          break
      else:
        chargedDate = parser.parse(row[1]).date()
        charge_date = datetime.combine(chargedDate, time.min)
        salesData['charged_date'] = str(charge_date)
        salesData['date'] = chargedDate
        if not(start_date <= chargedDate <= end_date):
          continue
        financialStatus = row[3]
        itemPrice = _parse_decimal(row[10])
        chargedAmt = _parse_decimal(row[12])
        saleCurrency = row[9]
        salesData['customer_id'] = int(customerId.customer_id)
        salesData['order_number'] = row[0]
        salesData['charged_time'] = str(from_timestamp(long(row[2]), utc))
        salesData['financial_status'] = row[3]
        salesData['device_model'] = row[4]
        salesData['product_title'] = row[5]
        salesData['product_id'] = row[6]
        salesData['product_type'] = row[7]
        salesData['sku_id'] = row[8]
        salesData['sale_currency'] = row[9]
        salesData['item_price'] = str(_parse_decimal(row[10]))
        salesData['taxes'] = str(_parse_decimal(row[11]))
        salesData['charged_amount'] = str(_parse_decimal(row[12]))
        salesData['buyer_city'] = row[13]
        salesData['buyer_state'] = row[14]
        salesData['buyer_postal_code'] = row[15]
        salesData['buyer_country'] = row[16]
        salesData['timestamp'] = row[2]

        paymentDirection = -1 if (financialStatus == 'Refund' or chargedAmt < 0) else 1
        developerProceeds = paymentDirection * itemPrice * _GOOGLE_DEVELOPER_REVENUE_SHARE
        googleFee = itemPrice * _GOOGLE_FEE
        developerProceedsUsd = convert_decimal_to_usd(developerProceeds,
            saleCurrency).quantize(TEN_PLACES)
        
        salesData['developer_proceeds'] = str(developerProceeds)
        salesData['developer_proceeds_usd'] = str(developerProceedsUsd)
        todayUtc = datetime.now()
        salesData['creation_time'] = str(todayUtc)
        salesData['last_modified'] = str(todayUtc)
        
        records.append(salesData)
    #records = sorted(records, key=lambda x: x['timestamp'],reverse=True)
    return records

class GoogleEarningsReportProcessor(object):
  def process(self, report_location, start_date, end_date):
    compressedData = StringIO()

    # Unavailable monthly report files will manifest as InvalidUriErrors.
    try:
      storageUri = storage_uri(report_location)
      storageUri.connection = connect_gs()
      storageUri.get_contents_to_stream(compressedData)
    except InvalidUriError as e:
      raise ReportUnavailableException('Report not yet available: %s' % e.message)

    zipData = ZipFile(compressedData)

    # We expect exactly one file in the archive.
    zipFilename = zipData.namelist()[0]
    salesReportFile = zipData.open(zipFilename)
    reader = csv.reader(salesReportFile.readlines(), delimiter=',')
    records = []
    for i, row in enumerate(reader):
		copied_c = {}
		if i == 0:
			if _GOOGLE_EARNING_REPORT_EXPECTED_FIELDS != row[:len(_GOOGLE_EARNING_REPORT_EXPECTED_FIELDS)]:
				logger.warning('Encountered unexpected google report fields: %s' % row)
				break
		else:
			chargedDate = parser.parse(row[1]).date()
			if not(start_date <= chargedDate <= end_date):
				continue
			if 	row[4] == 'Google fee':
				copied_c['orderNumber'] = row[0]
				copied_c['product_id'] = row[7]
				copied_c['transactionType'] = row[4]
				copied_c['googleFee'] = abs(_parse_decimal(row[15]))
				copied_c['conversionRate'] = _parse_decimal(row[16])
				copied_c['merchantCurrency'] = row[17]
				copied_c['amountMerchantCurrency'] = _parse_decimal(row[18])
				records.append(copied_c)
			
    return records


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

GOOGLE_SALES_REPORT_PROCESSOR = GoogleSalesReportProcessor()
GOOGLE_INSTALLATION_REPORT_PROCESSOR = GoogleInstallationReportProcessor()
GOOGLE_EARNINGS_REPORT_PROCESSOR = GoogleEarningsReportProcessor()

GOOGLE_REPORT_TYPE_TO_PROCESSOR_MAP = {
  'installs': GOOGLE_INSTALLATION_REPORT_PROCESSOR,
  'sales': GOOGLE_SALES_REPORT_PROCESSOR,
  'earnings': GOOGLE_EARNINGS_REPORT_PROCESSOR,
}

def _parse_decimal(value_str):
  decimalStr = value_str.replace(',', '')
  return Decimal(decimalStr)

def _report_file_names(bucket_id, report_type, start_date, end_date, allfiles, app_id):
	if report_type not in _GOOGLE_REPORT_TYPES:
		raise ValueError('Unrecognized report type %s' % report_type)
	elif report_type in ['payouts', 'sales', 'earnings']:
		months = {}
		fileNames = []
		reportDate = start_date
		while reportDate <= end_date:
			months[reportDate.strftime('%Y%m')] = None
			reportDate += timedelta(days=28)
		if end_date >= start_date:
			months[end_date.strftime('%Y%m')] = None
		if report_type == 'sales':
			for m in months:
				filename = 'salesreport_' + m + '.zip'
				if filename in allfiles:
					fileNames.append(filename)
				#fileNames = ['salesreport_' + m + '.zip' for m in months]
		elif report_type == 'payouts':
			fileNames = ['payout_' + m + '.zip' for m in months]
		elif report_type == 'earnings':
			startDateFloor = date(year=start_date.year, month=start_date.month, day=1)
			endDateFloor = date(year=end_date.year, month=end_date.month, day=1)
			bucket = storage_uri(_GOOGLE_REPORT_BUCKET_BASE + bucket_id)
			for obj in bucket.list_bucket(prefix='earnings'):
				m = match(r'^earnings/(earnings_([\d]+)_([\d]+)-([\d]+).zip)$', obj.name)
				if m:
					# We expect YYYYMM format.
					reportDateStr = m.group(2)
					reportDateFloor = date(year=int(reportDateStr[:4]), month=int(reportDateStr[4:6]), day=1)
					if (startDateFloor <= reportDateFloor <= endDateFloor) and (start_date <= end_date):
						fileNames.append(m.group(1))
		return fileNames
  
	elif report_type == 'installs':
		fileNames = []
		startDateFloor = date(year=start_date.year, month=start_date.month, day=1)
		endDateFloor = date(year=end_date.year, month=end_date.month, day=1)
		bucket = storage_uri(_GOOGLE_REPORT_BUCKET_BASE + bucket_id)
		if app_id is not None:
			prefix_value = 'stats/installs/installs_'+app_id
		else:
			prefix_value = 'stats/installs/installs'
			
		for obj in bucket.list_bucket(prefix=prefix_value):
			m = match(r'^stats/installs/(installs_[^_]+_([\d]+)_country.csv)$', obj.name)
			if m:
				# We expect YYYYMM format.
				reportDateStr = m.group(2)
				reportDateFloor = date(year=int(reportDateStr[:4]), month=int(reportDateStr[4:6]), day=1)
				if (startDateFloor <= reportDateFloor <= endDateFloor) and (start_date <= end_date):
					#print m.group(1)
					fileNames.append(m.group(1))
		return fileNames
	else:
		raise NotImplementedError

def _report_folder(report_type):
  if report_type not in _GOOGLE_REPORT_TYPES:
    raise ValueError('Unrecognized report type %s' % report_type)
  elif report_type in ['payouts', 'sales', 'earnings']:
    return report_type
  elif report_type == 'installs':
    return 'stats/installs'
  else:
    raise NotImplementedError

def fetch_google_daily_sales_report(refresh_token, bucket_id, report_date=None):
  # Warning: this defaults to UTC date.
  if not report_date:
    report_date = date.today() - timedelta(days=1)
  return fetch_google_report(refresh_token, bucket_id, report_type='sales', start_date=report_date,
      end_date=report_date)

def fetch_google_report(refresh_token, bucket_id, report_type, start_date, end_date, customerId, app_id):
	if report_type not in _GOOGLE_REPORT_TYPES:
		raise ValueError('Unrecognized report type %s' % report_type)
	elif report_type not in ['installs', 'sales', 'earnings']:
		raise NotImplementedError('No report fetching enabled for report type %s' % report_type)
	
	scriber_gcs_boto_plugin.SetAuthInfo(refresh_token)

	# The request_nonce is only used to disambiguate requests made within short times of one another.
	# Uniqueness is not required.
	request_nonce = b64encode(urandom(10)).rstrip('==')
	request_time = from_timestamp(utc_epoch(), utc)
	reportFolder = _report_folder(report_type)
  
	sales_files_location = '/'.join([_GOOGLE_REPORT_BUCKET_BASE + bucket_id, reportFolder])
	src_uri = storage_uri(sales_files_location)
	all_files = []
	for key in src_uri.list_bucket(report_type):
		key_name = key.name
		filename = key_name.split('/')[-1]
		all_files.append(filename)
	

	reportFileNames = _report_file_names(bucket_id, report_type, start_date, end_date, all_files, app_id)
	#print reportFileNames
	
	records = []
	for reportFileName in reportFileNames:
		reportLocation = '/'.join([_GOOGLE_REPORT_BUCKET_BASE + bucket_id, reportFolder, reportFileName])
		reportProcessor = GOOGLE_REPORT_TYPE_TO_PROCESSOR_MAP[report_type]
		fileRecords = reportProcessor.process(reportLocation, start_date, end_date, customerId)
		if fileRecords:
			records.extend(fileRecords)
	
	if records:
		if report_type == 'earnings':
			for record in records:
				order_number = record['orderNumber']
				reportInfos = retrieve_from_db(order_number)
				if reportInfos.count() != 0:
					for reportInfo in reportInfos:
						record_id = reportInfo.record_id
						reportInfo.google_fee = record['googleFee']
						reportInfo.currency_conversion_rate = record['conversionRate']
						reportInfo.merchant_currency = record['merchantCurrency']
						reportInfo.save()
		elif report_type == 'installs':
			#pass
			records = sorted(records, key=lambda x: x['date'],reverse=True)
			"""
			for record in records:
				country = record.country
				date = record.date
				package_name = record.package_name
				reportInfo = retrieve_install_record(country,date,package_name)
				if reportInfo.count() == 0:
					record.customer_id = customerId
					record.save()
			"""
		else:
			#pass
			records = sorted(records, key=lambda x: x['timestamp'],reverse=True)
			"""	
			for record in records:
				order_number = record.order_number
				financial_status = record.financial_status
				reportInfo = retrieve_from_db(order_number,financial_status)
				if reportInfo.count() == 0:
					record.customer_id = customerId
					record.save()
			"""	
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
