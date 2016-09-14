import logging

from base64 import b64encode
from core.cache import cache_results
from customers.models import CustomerApiKey
from hashlib import sha256, sha384
from os import urandom
from random import choice

logger = logging.getLogger(__name__)

# Cache results of this call for 30 minutes since we will have few API keys.
# @cache_results(timeout=30*60)
def is_valid(api_key):
  try:
    CustomerApiKey.objects.get(api_key=api_key)
  except CustomerApiKey.DoesNotExist:
    logger.info("Received unrecognized API key: %s" % api_key)
    return False
  except CustomerApiKey.MultipleObjectsReturned:
    # This should never happen since apiKey is a column with a unique constraint.
    logger.error("Query returned multiple customers matching an API key: %s" % api_key)
    # TODO(d-felix): Raise an alert.
    return False
  except Exception as e:
    logger.info("Customer API key lookup failed with message: %s" % e.message)
    return False
  return True

def is_valid_format(api_key):
  """ Indicates whether the provided string has the correct format for an API key."""
  if api_key is None or len(api_key) != 43:
    return False
  elif api_key.isalnum():
    return True
  return False

def new_api_key(bytes=128):
  """
  Generates a new alphanumeric API key using the provided number of bytes of randomness.

  Keyword arguments:
  bytes -- the number of bytes to be used for a random seed
  """
  # Current implementation:
  # 1. Draw random input from os.urandom(bytes).
  # 2. Apply hashlib.sha256() to the input.
  # 3. Base64 encode the output, replacing non-alphanumeric characters using one of the ten provided
  #    character sequences at (pseudo-)random.
  # 4. Remove any trailing padding characters.
  return b64encode(sha256(urandom(bytes)).digest(),
      choice(['4n', 'rB', 'zr', 'wP', 'vz', 'Kd', 'IA', 'ES', 'us', '4u'])).rstrip('==')
