# Note that BACKOFF_MAX_SECS is chosen to less than the Redis visibility timeout of 5 hours.
BACKOFF_MAX_SECS = 14400  # 4 hours
BACKOFF_MIN_SECS = 180
BACKOFF_BASE = 2
BACKOFF_SCALE = 60

def exponential_backoff(exponent):
  """
  A simple common utility function for computing celery retry countdown values.
  """
  return _exponential_backoff(exponent, BACKOFF_MIN_SECS, BACKOFF_MAX_SECS,
      BACKOFF_BASE, BACKOFF_SCALE)

def _exponential_backoff(exponent, minimum, maximum, base, scale):
  unbounded_result = scale * (base ** exponent)
  bounded_result = min(maximum, max(minimum, unbounded_result))
  return bounded_result