from core.timeutils import utc_epoch
from django.core.cache import cache
import logging 

_CACHE_KEY_PREFIX = 'ephemera'
_CACHE_KEY_IDENTIFIER = 'gfNf0Gdw9QCKUhP5'
_KEY_DELIMITER = '/'

EPHEMERA_TIMEOUT_SECS = 60 * 60 * 4

# TODO(d-felix): Synchronization
# WARNING: These functions will not behave well at scale without distributed
# locking. Use at your own risk.

def _cache_key(customer_id):
  return _KEY_DELIMITER.join([_CACHE_KEY_PREFIX, _CACHE_KEY_IDENTIFIER, str(customer_id)])

def _set_keys(customer_id, keys):
  cacheKey = _cache_key(customer_id)
  cache.set(cacheKey, keys, EPHEMERA_TIMEOUT_SECS)

def get_keys(customer_id):
  cacheKey = _cache_key(customer_id)
  logging.info(cacheKey)
  keys = cache.get(cacheKey)
  logging.info(keys)

  # Remove expired items before returning results.
  if keys:
    keysToPop = []
    for key in keys:
      keyAge = utc_epoch() - keys[key]['creation_time']
      if keyAge >= EPHEMERA_TIMEOUT_SECS:
        keysToPop.append(key)
    for key in keysToPop:
      keys.pop(key, None)
    _set_keys(customer_id, keys)

  return keys

def get_keys_for_topic(customer_id, topic):
  keys = get_keys(customer_id)
  ret = {}
  for key in keys:
    if keys[key]['topic'] == topic:
      ret[key] = keys[key]
  return ret

def set_key(customer_id, key, topic):
  if not (customer_id and key and topic):
    raise ValueError('Cannot set ephemera with missing arguments')
  keys = get_keys(customer_id)
  keys = {} if keys is None else keys
  keys[key] = {'topic': topic, 'creation_time': utc_epoch()}
  _set_keys(customer_id, keys)
