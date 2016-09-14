"""
A collection of time-related utility functions.
"""
import time

from calendar import timegm
from datetime import datetime
from pytz import timezone

# A timezone-unaware date display format
DATE_FMT = "%Y-%m-%d"
CHART_DATE_FMT = "%m/%d/%Y"

# A timezone-unaware datetime display format
TFMT = "%Y-%m-%d %H:%M:%S"

# A timezone-aware datetime display format
TZ_TFMT = "%Y-%m-%d %H:%M:%S %Z%z"

def serialize_unaware(dt):
  """
  Returns a string representation of a timezone-unaware datetime.
  The tzinfo of a timezone-aware argument is ignored.
  """
  return dt.strftime(TFMT)

def deserialize_unaware(dt_str):
  """
  Returns a timezone-unaware datetime from a string representation that is the result of calling
  serialize_unaware().  Alternate formats are not supported.
  """
  return datetime.strptime(dt_str, TFMT)

def display(dt):
  """ Returns string representation of a timezone-aware datetime. """
  return dt.strftime(TZ_TFMT)

def convert_tz(dt, old_tz, new_tz):
  """
  Returns the timzone-aware datetime that is the result of converting the provided datetime from
  the timezone old_tz to the timezone new_tz.

  The provided datetime object is assumed to be timezone-unaware, and any tzinfo present is ignored.
  """
  return  old_tz.localize(strip_tz(dt)).astimezone(new_tz)

def from_timestamp(timestamp, timezone):
  """
  Returns a timezone-aware datetime from a numeric timestamp and desired timezone.
  Performs a crude detection of the scale (seconds vs. millis vs. nanos) of the timestamp.
  """
  while timestamp > long(1e10):
    timestamp /= 1000
  return datetime.fromtimestamp(timestamp, timezone)

def timestamp(dt_arg):
  """
  Returns the UNIX timestamp for the provided datetime object.
  Arguments without timezones are treated as being UTC times.
  """
  dt = dt_arg.replace(tzinfo=timezone('UTC')) if dt_arg.tzinfo is None else dt_arg
  return timegm(dt.utctimetuple())

def midnight_timestamp(date, tz):
  """
  Returns the UNIX timestamp corresponding to midnight on the provided date in the provided
  timezone.
  """
  dateAtMidnight = datetime.combine(date, datetime.min.time())
  dt = convert_tz(dateAtMidnight, tz, timezone('UTC'))
  return timegm(dt.utctimetuple())

def strip_tz(dt):
  """ Returns a timezone-unaware datetime by stripping away any tzinfo. """
  return dt.replace(tzinfo=None)

def today(tz=timezone('UTC')):
  """
  Returns the current date (timezone-unaware) for the given timezone.
  """
  currentTime = datetime.utcfromtimestamp(utc_epoch())
  convertedCurrentTime = convert_tz(currentTime, timezone('UTC'), tz)
  return convertedCurrentTime.date()

def utc_epoch():
  """ Returns the number of seconds elapsed since 12:00am UTC, January 1, 1970. """
  return int(time.time())
