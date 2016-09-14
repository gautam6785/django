import unittest

from core.cache import _cache_key_prefix, cache_key, cache_results
from django.core.cache import cache

# Set the cache expiration timeout to 5 minutes for testing
TEST_TIMEOUT = 5*60

# Constant strings used for testing
EXPECTED_RESULT = 'Expected result'
NEW_VALUE = 'New value'
OLD_VALUE = 'Old value'

@cache_results(timeout=TEST_TIMEOUT)
def test_func(arg, *args, **kwargs):
  return arg

@cache_results(timeout=TEST_TIMEOUT)
def test_func2(arg, *args, **kwargs):
  return arg

class CacheTests(unittest.TestCase):
  def testPrefixDependsOnFunc(self):
    self.assertNotEqual(_cache_key_prefix(test_func), _cache_key_prefix(test_func2))

  def testKeyContainsPrefix(self):
    self.assertTrue(_cache_key_prefix(test_func) in cache_key(test_func, 0, {'newArg': 1}))

  def testKeyDependsOnArgs(self):
    self.assertNotEqual(cache_key(test_func, 0), cache_key(test_func, 1))

  def testKeyDependsOnKwargs(self):
    self.assertNotEqual(cache_key(test_func, {'newArg': 0}), cache_key(test_func, {'newArg': 1}))

  def testCachePopulation(self):
    # Delete any value for the key that we'll use in this test.
    key = cache_key(test_func, EXPECTED_RESULT, {'newArg': 1})
    cache.delete(key)
    self.assertEquals(cache.get(key), None)

    # Call the decorated function with the expected arguments.
    test_func(EXPECTED_RESULT, {'newArg': 1})

    # Check that the function call populated the cache correctly.
    self.assertEquals(cache.get(key), EXPECTED_RESULT)

  def testCacheRetrieval(self):
    # In this test we use a closure to control the true return value of a decorated function.
    def make_test_func3(argList):
      @cache_results(timeout=TEST_TIMEOUT)
      def test_func3():
        # This function maintains its own reference to the passed argList, so we cannot simply pass
        # in a primitive and rebind it later.  Instead, we pass in a list and then modify its
        # contents when required.
        return argList[0]
      return test_func3

    # Create the decorated function to be tested.
    argList = [OLD_VALUE]
    test_func3 = make_test_func3(argList)

    # Delete any value for the key that we'll use in this test.
    key = cache_key(test_func3)
    cache.delete(key)
    self.assertEquals(cache.get(key), None)

    # Call the decorated function and check that the cache is populated correctly.
    test_func3()
    self.assertEquals(cache.get(key), OLD_VALUE)

    # Change the underlying value to be returned
    argList[0] = NEW_VALUE

    # Call the decorated function and check that the cached value is returned.
    self.assertEquals(test_func3(), OLD_VALUE)

    # Clear the cached value and check that the test function now returns the new value.
    cache.delete(key)
    self.assertEquals(test_func3(), NEW_VALUE)

if __name__ == '__main__':
  unittest.main()
