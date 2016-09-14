import logging

from django.conf import settings
from os import getpid, path
from selenium import webdriver

logger = logging.getLogger(__name__)

# This wrapper class allows for lazy initialization of its enclosed
# PhantomJS webdriver.
class PhantomJsWrapper(object):
  def __init__(self):
    self.driver = None
    self.started = False

  def start(self):
    logger.info('Starting PhantomJS from process %s' % getpid())

    # Disable GhostDriver logging since it's not threadsafe.
    # TODO(d-felix): Write a patch if we really care about these logs, though I
    # suspect that we do not.
    self.driver = webdriver.PhantomJS(service_log_path=path.devnull)
    self.driver.implicitly_wait(10)
    self.driver.set_window_size(1024, 768)
    self.started = True

  def stop(self):
    self.driver.quit()
    self.driver = None
    self.started = False

  def get_webdriver(self):
    return self.driver

# This module-scope wrapper acts as lazy singleton.
_PHANTOM_JS = PhantomJsWrapper()

def start_phantom_js():
  if not _PHANTOM_JS.started:
    _PHANTOM_JS.start()

def stop_phantom_js():
  if _PHANTOM_JS.started:
    _PHANTOM_JS.stop()

def phantom_js():
  start_phantom_js()
  return _PHANTOM_JS.get_webdriver()
