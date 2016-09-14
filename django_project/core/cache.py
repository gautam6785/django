import logging

from django.core.cache import cache
from functools import wraps

logger = logging.getLogger(__name__)

KEY_DELIMITER = '/'
PROJECT_PREFIX = 'appserver'

def _always(*args, **kwargs):
  return True

def _first_arg_is_not_none(arg, *args, **kwargs):
  return arg is not None

def _cache_key_prefix(func):
  """
  Returns the portion of the cache key that identifies the function being called.
  """
  return KEY_DELIMITER.join([PROJECT_PREFIX, func.__module__, func.__name__])

def cache_key(func, *args, **kwargs):
  """
  Returns a string cache key for a function call.
  """
  # TODO(d-felix): Escape the elements argStrList intelligently with respect to KEY_DELIMITER.
  argStrList =  [str(i) for i in sorted(args) + sorted(kwargs.items())]
  return KEY_DELIMITER.join([_cache_key_prefix(func)] + argStrList)

# Default to a 5 minute expiration
def cache_results(timeout=5*60, consult_cache=_always, update_cache=_first_arg_is_not_none):
  def cache_results_decorator(func):
    """
    A decorator that caches its wrapped function calls.
    Methods belonging to distinct objects of a single class share keyspaces, so caching is not
    performed on a per-instance basis.
    """
    @wraps(func)
    def decorated_func(*args, **kwargs):
      key = cache_key(func, *args, **kwargs)
      if consult_cache(*args, **kwargs):
        result = cache.get(key)
        if result is not None:
          return result
      result = func(*args, **kwargs)

      # By default, don't cache None
      if update_cache(result, *args, **kwargs):
        cache.set(key, result, timeout)

      return result
    return decorated_func
  return cache_results_decorator
