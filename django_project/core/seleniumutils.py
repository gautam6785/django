import time
import logging

from selenium.common.exceptions import StaleElementReferenceException

_INVALID_ELEMENT_ID = 'lgxAxzGFu2ttdb7enF3e5SB3VSzBktOzquVFfsWjw3qFcj3fDHEnH9DnvjYPIIJ'

def wait_for(condition_function, timeout_secs=3, sleep_duration=0.1):
  logging.info("waiting")
  start_time = time.time()
  logging.info("start time")
  logging.info(start_time)
  logging.info('<')
  logging.info(start_time + timeout_secs)
  while time.time() < start_time + timeout_secs:
    logging.info('starting loop')
    logging.info(time.time())
    logging.info('<')
    logging.info(start_time + timeout_secs)
    if condition_function():
      logging.info("condition met")
      return True
    else:
      logging.info("sleeping")
      time.sleep(sleep_duration)
  raise Exception('Timeout waiting for %s' % condition_function.__name__)

def click_through_to_new_page(link, timeout_secs=3, sleep_duration=0.1):
  link.click()

  def link_has_gone_stale():
    try:
      # poll the link with an arbitrary call
      link.find_elements_by_id(_INVALID_ELEMENT_ID) 
      return False
    except StaleElementReferenceException:
      return True

  wait_for(link_has_gone_stale, timeout_secs, sleep_duration)

def submit_to_new_page(form_element, timeout_secs=3, sleep_duration=0.1):
  logging.info("submit")
  form_element.submit()

  def link_has_gone_stale():
    try:
      # poll the link with an arbitrary call
      logging.info("link gone stale try")
      form_element.find_elements_by_id(_INVALID_ELEMENT_ID) 
      logging.info("found eles")
      return False
    except StaleElementReferenceException:
      logging.info("link gone stale exeception")
      return True

  wait_for(link_has_gone_stale, timeout_secs, sleep_duration)
