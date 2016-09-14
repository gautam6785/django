import unittest

from core.scriberid import is_valid_format, new_scriber_id

VALID_KEY_LENGTH = 64

class ScriberIdTests(unittest.TestCase):
  def testNoneOrEmptyIsInvalid(self):
    self.assertFalse(is_valid_format(None))
    self.assertFalse(is_valid_format(''))

  def testLengthMustBeCorrect(self):
    scriber_id = "a" * (VALID_KEY_LENGTH - 1)
    self.assertFalse(is_valid_format(scriber_id))
    scriber_id += "a"
    self.assertTrue(is_valid_format(scriber_id))
    scriber_id += "a"
    self.assertFalse(is_valid_format(scriber_id))

  def testNonAlphanumericCharactersInvalid(self):
    scriber_id_prefix = "a" * (VALID_KEY_LENGTH - 1)
    scriber_id = scriber_id_prefix + "+"
    self.assertFalse(is_valid_format(scriber_id))
    scriber_id = scriber_id_prefix + "\\"
    self.assertEquals(len(scriber_id), VALID_KEY_LENGTH)
    self.assertFalse(is_valid_format(scriber_id))

  def testNewScriberIdIsValid(self):
    self.assertTrue(is_valid_format(new_scriber_id()))
    self.assertTrue(is_valid_format(new_scriber_id(1024)))

if __name__ == '__main__':
  unittest.main()
