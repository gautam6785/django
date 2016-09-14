import logging
from django.contrib.auth.models import User

from calendar import timegm
from copy import deepcopy
from core.timeutils import convert_tz, display, from_timestamp, midnight_timestamp, timestamp, DATE_FMT
from customers.models import Customer, CustomerExternalLoginInfo
from datetime import datetime, timedelta
from django.db import connection
from pytz import timezone
from appinfo.models import AppInfo

logger = logging.getLogger(__name__)

_RECENT_SESSION_THRESHOLD_DAYS = 28


def product_info_for_auth_user(userId, **kwargs):
	
	results = {}
	appinfos = AppInfo.objects.filter(customer_id=userId)
	for appinfo in appinfos:
		results['product_id_string'] = appinfo.app
		results['platform'] = appinfo.platform
		
	return results

def time_info_from_bounds(userId, start_in_seconds, end_in_seconds):
  customer = Customer.objects.get(auth_user__id=userId)
  customerTz = timezone(customer.timezone)
  startDate = from_timestamp(float(start_in_seconds), customerTz).date()
  endDate = from_timestamp(float(end_in_seconds), customerTz).date()
  previousEndDate = startDate - timedelta(days=1)
  previousStartDate = previousEndDate - (endDate - startDate)

  times = []
  previousTimes = []

  # Construct the list of times corresponding to midnight on the appropriate day.
  for delta in range((endDate - startDate + timedelta(days=1)).days):
    date = startDate + timedelta(days=delta)
    previousDate = previousStartDate + timedelta(days=delta)
    times.append(midnight_timestamp(date, customerTz))
    previousTimes.append(midnight_timestamp(previousDate, customerTz))

  return {
      'times': times,
      'start_date': startDate,
      'end_date': endDate,
      'previous_times': previousTimes,
      'previous_start_date': previousStartDate,
      'previous_end_date': previousEndDate
  }
