import csv
import logging
import requests
import zlib

from base64 import b64encode
from core.currency import convert_decimal_to_usd
from core.db.constants import TEN_PLACES, TWO_PLACES
from core.timeutils import from_timestamp, utc_epoch
#from datetime import date, timedelta
from datetime import date, datetime, time, timedelta
from dateutil import parser
from decimal import Decimal
from django.db import transaction
from metrics.models import AppleReportRecord
from os import urandom
from pytz import utc

_ITUNES_DEVELOPER_REVENUE_SHARE = Decimal('0.7')
_ITUNES_FEE = Decimal('0.3')

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
]

logger = logging.getLogger(__name__)

# Indicates a generic failure when trying to pull a report.
class ReportFetchException(Exception):
  pass

# An exception indicating that a report is not yet available.
class ReportUnavailableException(ReportFetchException):
  pass
  
def fetch_apple_daily_sales_report(username, password, vendor_id, report_date=None):
  # Warning: this defaults to UTC date.
  if not report_date:
    report_date = date.today() - timedelta(days=1)
  return fetch_apple_report(username, password, vendor_id, report_type='Sales',
      date_type='Daily', report_subtype='Summary', report_date=report_date)

def fetch_apple_report(username, password, vendor_id, report_type, date_type,
    report_subtype, report_date):
  report_date_str = report_date.strftime('%Y%m%d')
  params = ({
    "USERNAME" : username,
    "PASSWORD" : password,
    "VNDNUMBER" : vendor_id,
    "TYPEOFREPORT" : report_type,
    "DATETYPE" : date_type,
    "REPORTTYPE" : report_subtype,
    "REPORTDATE" : report_date_str
  })

  request_time = from_timestamp(utc_epoch(), utc)
  # The request_nonce is only used to disambiguate requests made within short times of one another.
  # Uniqueness is not required.
  request_nonce = b64encode(urandom(10)).rstrip('==')
  response = requests.post(_APPLE_REPORT_URL_BASE, headers=_APPLE_REPORT_HEADERS, params=params)
  #print response.headers

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
        provider = row[0]
        provider_country = row[1]
        sku = row[2]
        developer = row[3] if row[3] != '' else None
        title = row[4]
        version = row[5] if row[5] != '' else None
        product_type_identifier = row[6]
        units = Decimal(row[7]).quantize(TWO_PLACES)
        developer_proceeds = Decimal(row[8]).quantize(TWO_PLACES)
        begin_date = parser.parse(row[9]).date()
        end_date = parser.parse(row[10]).date()
        customer_currency = row[11]
        country_code = row[12]
        currency_of_proceeds = row[13]
        apple_identifier = long(row[14])
        customer_price = Decimal(row[15]).quantize(TWO_PLACES)
        promo_code = row[16] if row[16] != '' else None
        parent_identifier = row[17] if row[17] != '' else None
        subscription = row[18] if row[18] != '' else None
        period = row[19] if row[19] != '' else None
        category = row[20]
        cmb = row[21] if row[21] != '' else None

        total_developer_proceeds = units * developer_proceeds
        developerProceeds = total_developer_proceeds * _ITUNES_DEVELOPER_REVENUE_SHARE
        developer_proceeds_usd = convert_decimal_to_usd(total_developer_proceeds,
            currency_of_proceeds).quantize(TEN_PLACES)
        records.append(AppleReportRecord(
          customer_id=customerId, provider=provider, provider_country=provider_country, sku=sku, developer=developer,
          title=title, version=version, product_type_identifier=product_type_identifier,
          units=units, developer_proceeds=developer_proceeds, begin_date=begin_date,
          end_date=end_date, customer_currency=customer_currency, country_code=country_code,
          currency_of_proceeds=currency_of_proceeds, apple_identifier=apple_identifier,
          customer_price=customer_price, promo_code=promo_code, parent_identifier=parent_identifier,
          subscription=subscription, period=period, category=category, cmb=cmb,
          developer_proceeds_usd=developer_proceeds_usd))
		"""
    return records

  else:
    raise ReportFetchException('An unexpected error occurred. Received response headers: %s' %
        response.headers)


def fetch_itunes_download_report(username,password,vendor_id,report_type,date_type,report_subtype,report_date_str, app_identifier):
	
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
			#raise ReportUnavailableException('Report not yet available')
			records = []
		else:
			#raise ReportFetchException(response.headers['errormsg'])
			records = []
	elif 'filename' in response.headers and response.headers['filename']:
		decompressed_data=zlib.decompress(response.content, 16+zlib.MAX_WBITS)
		reader = csv.reader(decompressed_data.splitlines(), delimiter='\t')
		records = []
		for i, row in enumerate(reader):
			downloadData = {}
			if i == 0:
				if _APPLE_REPORT_EXPECTED_FIELDS != row[:len(_APPLE_REPORT_EXPECTED_FIELDS)]:
					logger.warning('Encountered unexpected apple report fields: %s' % row)
					break
			else:
				units = int(row[7])
				identifier = long(row[14])
				product_type_identifier = row[6]
				if(identifier == app_identifier and units > 0 and (product_type_identifier == '1F' or product_type_identifier == 1)):
					downloadData['provider'] = row[0]
					downloadData['provider_country'] = row[1]
					downloadData['sku'] = row[2]
					downloadData['title'] = row[4]
					downloadData['product_type_identifier'] = row[6]
					downloadData['units'] = str(_parse_decimal(row[7]))
					downloadData['begin_date'] = parser.parse(row[9]).date()
					downloadData['end_date'] = parser.parse(row[10]).date()
					downloadData['country_code'] = row[12]
					downloadData['apple_identifier'] = long(row[14])
					records.append(downloadData)
			
		return records

def fetch_itunes_sales_report(username,password,vendor_id,report_type,date_type,report_subtype,report_date_str, app_identifier):
	
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
			#raise ReportUnavailableException('Report not yet available')
			records = []
		else:
			#raise ReportFetchException(response.headers['errormsg'])
			records = []
	elif 'filename' in response.headers and response.headers['filename']:
		decompressed_data=zlib.decompress(response.content, 16+zlib.MAX_WBITS)
		reader = csv.reader(decompressed_data.splitlines(), delimiter='\t')
		records = []
		parentIdenifier =[]
		for i, row in enumerate(reader):
			salesData = {}
			if i == 0:
				if _APPLE_REPORT_EXPECTED_FIELDS != row[:len(_APPLE_REPORT_EXPECTED_FIELDS)]:
					logger.warning('Encountered unexpected apple report fields: %s' % row)
					break
			else:
				identifier = long(row[14])
				sku = row[2]
				if(identifier == app_identifier):
					if sku not in parentIdenifier:
						parentIdenifier.append(sku)		
				units = int(row[7])
				salesData['provider'] = row[0]
				salesData['provider_country'] = row[1]
				salesData['sku'] = row[2]
				salesData['developer'] = row[3] if row[3] != '' else None
				salesData['title'] = row[4]
				salesData['version'] = row[5] if row[5] != '' else None
				salesData['product_type_identifier'] = row[6]
				salesData['units'] = int(row[7])
				salesData['price'] = row[8]
				developer_proceeds = _parse_decimal(row[8])
				salesData['begin_date'] = parser.parse(row[9]).date()
				salesData['end_date'] = parser.parse(row[10]).date()
				salesData['customer_currency'] = row[11]
				salesData['country_code'] = row[12]
				currency_of_proceeds = row[13]
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
				
				salesData['developer_proceeds'] = str(developerProceeds)
				salesData['developer_proceeds_usd'] = str(developerProceedsUsd)
				records.append(salesData)
		
		return records, parentIdenifier

def _parse_decimal(value_str):
  decimalStr = value_str.replace(',', '')
  return Decimal(decimalStr)
