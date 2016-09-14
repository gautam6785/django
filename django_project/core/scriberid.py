from base64 import b64encode
from hashlib import sha256, sha384
from os import urandom
from random import choice


def is_valid_format(external_scriber_id):
  """ Indicates whether the provided string has the correct format for an external scriber ID."""
  if external_scriber_id is None or len(external_scriber_id) != 64:
    return False
  elif external_scriber_id.isalnum():
    return True
  return False

def new_scriber_id(bytes=128):
  """
  Generates a new alphanumeric external scriber ID using the provided number of bytes of
  randomness.

  Keyword arguments:
  bytes -- the number of bytes to be used for a random seed
  """
  # Current implementation:
  # 1. Draw random input from os.urandom(bytes).
  # 2. Apply hashlib.sha384() to the input.
  # 3. Base64 encode the output, replacing non-alphanumeric characters using one of the ten
  #    provided character sequences at (pseudo-)random.
  # 4. Remove any trailing padding characters.
  #
  # The current implementation is nearly identical to apikey.new_api_key(), with the exception
  # that sha384 is used in order to provide longer output.
  # The high number of characters is used to (virtually) guarantee uniqueness so that new IDs may
  # be generated without consulting a database (i.e. we strive for a highly birthday-collision
  # resistant scheme).
  return b64encode(sha384(urandom(bytes)).digest(),
      choice(['96', '7S', 'eN', 'EG', 'Qm', 'lw', 'JH', 'Dx', 'b9', 'it'])).rstrip('==')
