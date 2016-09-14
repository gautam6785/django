import unittest

from core.apikey import is_valid_format, new_api_key

VALID_KEY_LENGTH = 43

class ApiKeyTests(unittest.TestCase):
  def testNoneOrEmptyIsInvalid(self):
    self.assertFalse(is_valid_format(None))
    self.assertFalse(is_valid_format(''))

  def testLengthMustBeCorrect(self):
    api_key = "a" * (VALID_KEY_LENGTH - 1)
    self.assertFalse(is_valid_format(api_key))
    api_key += "a"
    self.assertTrue(is_valid_format(api_key))
    api_key += "a"
    self.assertFalse(is_valid_format(api_key))

  def testNonAlphanumericCharactersInvalid(self):
    api_key_prefix = "a" * (VALID_KEY_LENGTH - 1)
    api_key = api_key_prefix + "+"
    self.assertFalse(is_valid_format(api_key))
    api_key = api_key_prefix + "\\"
    self.assertEquals(len(api_key), VALID_KEY_LENGTH)
    self.assertFalse(is_valid_format(api_key))

  def testNewApiKeyIsValid(self):
    self.assertTrue(is_valid_format(new_api_key()))
    self.assertTrue(is_valid_format(new_api_key(1024)))

if __name__ == '__main__':
  unittest.main()
