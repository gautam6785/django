from __future__ import absolute_import

import re
import requests
import time

from billiard import current_process
from celery import task
from celery.signals import worker_process_init, worker_process_shutdown
from celery.utils.log import get_task_logger
from core.celeryutils import exponential_backoff
from core.oauth.constants import GSUTIL_CLIENT_ID, GSUTIL_CLIENT_NOTSOSECRET
from core.seleniumutils import click_through_to_new_page
from core.utils import unpack
from customers.models import CustomerExternalLoginInfo
from customers import webdriverfactory
from django.conf import settings
from core.gcs_oauth2_boto_plugin import oauth2_client
from oauth2client.client import OAuth2WebServerFlow
from re import match
from string import split

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from selenium.selenium import selenium 
from pyvirtualdisplay import Display
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

from appinfo.constants import ANDROID_PLATFORM_STRING, IOS_PLATFORM_STRING
from appinfo.models import AppInfo, AppScreenshot
from appinfo import fetcher
from metrics.googlesalesreports import fetch_google_app_packages_name
from core.timeutils import from_timestamp, utc_epoch, DATE_FMT
from datetime import date, datetime, timedelta
from pytz import timezone, utc

_MAX_RETRIES = 5

AUTH_URI = 'https://accounts.google.com/o/oauth2/auth'
TOKEN_URI = 'https://accounts.google.com/o/oauth2/token'
REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'
SCOPE_READ_ONLY = 'https://www.googleapis.com/auth/devstorage.read_only'

APPLE_CSRF_SCRIPT_URL = 'https://reportingitc2.apple.com/ligerService/owasp/csrf-guard.js'
APPLE_REPORTS_API_URL_BASE = 'https://reportingitc2.apple.com/api/reports?_='
APPLE_REPORTS_URL = 'https://reportingitc2.apple.com/reports.html'
ITUNES_CONNECT_LOGIN_PAGE = 'https://itunesconnect.apple.com'

logger = get_task_logger(__name__)

# WARNING: Execution time for this initialization cannot exceed four seconds, or else the worker
# process will be killed under the assumption that it failed to start.
# TODO(d-felix): Investigate spawning a thread here to perform the PhantomJS initialization if we
# have trouble with the four second deadline.
@worker_process_init.connect
def init_worker_process_phantomjs(*args, **kwargs):
  if 'DefaultWorker' in current_process().initargs[1]:
    logger.info('Received worker_process_init signal, initializing PhantomJS')
    webdriverfactory.start_phantom_js()

@worker_process_shutdown.connect
def shutdown_worker_process_phantomjs(pid=None, exitcode=None, **kwargs):
  logger.info('Received worker_process_shutdown signal, quitting PhantomJS from worker process %s'
      % pid)
  webdriverfactory.stop_phantom_js()

def default_oauth2_client():
  cred_type=oauth2_client.CredTypes.OAUTH2_USER_ACCOUNT
  token_cache = oauth2_client.FileSystemTokenCache()

  return oauth2_client.OAuth2UserAccountClient(
      TOKEN_URI, GSUTIL_CLIENT_ID, GSUTIL_CLIENT_NOTSOSECRET, None,
      auth_uri=AUTH_URI, access_token_cache=token_cache,
      disable_ssl_certificate_validation=False,
      proxy_host=None, proxy_port=None, proxy_user=None, proxy_pass=None,
      ca_certs_file=None)


@task(max_retries=_MAX_RETRIES, ignore_result=True, bind=True)
def fetch_external_service_login_info(self, *args, **kwargs):
  try:
    (loginInfoId, ) = unpack(kwargs, 'login_info_id')
    loginInfo = CustomerExternalLoginInfo.objects.get(pk=loginInfoId)
    if loginInfo.external_service == CustomerExternalLoginInfo.GOOGLE_CLOUD:
      fetch_google_cloud_login_info.delay(login_info_id=loginInfoId)
    elif loginInfo.external_service == CustomerExternalLoginInfo.ITUNES_CONNECT:
      fetch_apple_vendor_id.delay(login_info_id=loginInfoId)
    else:
      logger.info('Not fetching external service login info for unrecognized service %s' %
          loginInfo.external_service)
      return
  except Exception as e:
    raise self.retry(exc=e, countdown=exponential_backoff(self.request.retries))


@task(max_retries=_MAX_RETRIES, ignore_result=True, bind=True)
def fetch_google_cloud_login_info(self, *args, **kwargs):
  try:
    driver = webdriverfactory.phantom_js()
    (loginInfoId, ) = unpack(kwargs, 'login_info_id')
    loginInfo = CustomerExternalLoginInfo.objects.get(pk=loginInfoId)

    oauthClient = default_oauth2_client()
    flow = OAuth2WebServerFlow(
        GSUTIL_CLIENT_ID, GSUTIL_CLIENT_NOTSOSECRET, [SCOPE_READ_ONLY],
        auth_uri=AUTH_URI, token_uri=TOKEN_URI, redirect_uri=REDIRECT_URI)
    approvalUrl = flow.step1_get_authorize_url()
    driver.delete_all_cookies()
    driver.get(approvalUrl)

    # Log in using the provided username and password.
    loginForm = driver.find_element_by_id("gaia_loginform")
    loginForm.find_element_by_id("Email").send_keys(loginInfo.username)
    
    nextButton = loginForm.find_element_by_id("next")
    nextButton.click()
    
    wait = WebDriverWait(driver, 10)
    password_input = wait.until(EC.visibility_of_element_located((By.ID,'Passwd')))
    
    #password_input = wait.until(EC.visibility_of_element_located((By.ID,'Passwd')))
    password_input.send_keys(loginInfo.password)
    
    #loginForm.find_element_by_id("Passwd").send_keys(loginInfo.password)
    
    signInButton = loginForm.find_element_by_id("signIn")
    click_through_to_new_page(signInButton, timeout_secs=10)

    # Approve the access request.
    approveAccessButton = driver.find_element_by_id('connect-approve').find_element_by_id(
        'submit_approve_access')
    click_through_to_new_page(approveAccessButton, timeout_secs=10)

    # Retrieve the authorization code.
    authorizationCode = driver.find_element_by_id('code').get_attribute('value')

    # Retrieve the credentials containing the refresh token.
    credentials = flow.step2_exchange(authorizationCode, http=oauthClient.CreateHttpRequest())
    refreshToken = credentials.refresh_token

    # Retrive the cloud storage bucket ID now that we're logged in.
    # This URL redirects to one having the bucket ID as a query parameter.
    driver.get('https://play.google.com/apps/publish/')
    urlWithBucketId = driver.current_url
    m = match(r'[^\?]*(\?[^#]+)+#*.*', urlWithBucketId)
    queryParams = {}
    queryParamStr = m.group(1)
    for param in split(queryParamStr, '?'):
      pair = split(param, '=')
      if len(pair) != 2:
        continue
      queryParams[pair[0]] = pair[1]
    bucketId = queryParams.get('dev_acc', None)
    if bucketId is None:
      logger.error('Could not parse cloud storage bucket ID from url %s' % urlWithBucketId)
      return

    # Save the refresh token and bucket ID to the database
    loginInfo.refresh_token = refreshToken
    loginInfo.gc_bucket_id = bucketId
    loginInfo.save()

  except Exception as e:
    raise self.retry(exc=e, countdown=exponential_backoff(self.request.retries))


@task(max_retries=_MAX_RETRIES, ignore_result=True, bind=True)
def fetch_apple_vendor_id(self, *args, **kwargs):
  try:
    driver = webdriverfactory.phantom_js()
    (loginInfoId, ) = unpack(kwargs, 'login_info_id')
    loginInfo = CustomerExternalLoginInfo.objects.get(pk=loginInfoId)

    if loginInfo.external_service != CustomerExternalLoginInfo.ITUNES_CONNECT:
      logger.info('Not fetching apple vendor id for foreign service: %s' %
          loginInfo.external_service)
      return

    driver.delete_all_cookies()

    driver.get(ITUNES_CONNECT_LOGIN_PAGE)
    wait = WebDriverWait(driver, 20)
    frame = wait.until(EC.visibility_of_element_located((By.ID,'authFrame')))
    driver.switch_to.frame(driver.find_element_by_id("authFrame"))
    appleId_input = wait.until(EC.visibility_of_element_located((By.ID,'appleId')))
    appleId_input.send_keys(loginInfo.username)
    password_input = wait.until(EC.visibility_of_element_located((By.ID,'pwd')))
    password_input.send_keys(loginInfo.password)
    signInButton = driver.find_element_by_id("sign-in")
    #click_through_to_new_page(signInButton, timeout_secs=10)
    signInButton.click()
    time.sleep(10)
    driver.switch_to.default_content()
    
    currentUrl = driver.current_url
    

    # TODO(d-felix): Get csrf-guard.js in a better way.
    driver.get(APPLE_CSRF_SCRIPT_URL)
    csrfScript = driver.find_element_by_tag_name('pre').text

    # Retrieve any cookies set by loading the reports page.
    driver.get(APPLE_REPORTS_URL)

    # Extract cookies for use in a handcrafted GET request.
    cookies = {}
    for cookie in driver.get_cookies():
      cookies[cookie['name']] = cookie['value']

    # Extract the token from the CSRF script.
    m = re.match(r'.*\"CSRF\", \"([A-Z0-9\-]+)\".*', csrfScript, re.DOTALL)
    csrfToken = m.group(1)

    # Construct special headers for the handcrafted request.
    headers = {'CSRF': csrfToken, 'X-Requested-With': 'OWASP CSRFGuard Project'}

    # Retrieve the report information using the private API.
    reportInfoUrl = APPLE_REPORTS_API_URL_BASE + str(long(time.time() * 1000))
    response = requests.get(reportInfoUrl, cookies=cookies, headers=headers)

    # Extract the vendor ID from the reponse.
    # Note that status code 200 responses are served for invalid requests.
    if not response.content:
      raise ValueError('Content missing from apple reports API response for login_info_id %s' %
          loginInfoId)
    reportInfo = response.json()
    try:
      entry = reportInfo['contents'][0] if 'contents' in reportInfo else reportInfo
      vendorIdStr = entry['reports'][0]['vendors'][0]['id']
    except Exception as e:
      raise ValueError('Encountered unrecognized apple reports API response: %s. ' +
          'Failed with message %s' % (reportInfo, e.message))
    vendorId = long(vendorIdStr)
    loginInfo.apple_vendor_id = vendorId
    loginInfo.save()

  except Exception as e:
    raise self.retry(exc=e, countdown=exponential_backoff(self.request.retries))



@task(max_retries=_MAX_RETRIES, ignore_result=True, bind=True)
def fetch_customer_google_apps(self, *args, **kwargs):
	try:
		(loginInfoId, ) = unpack(kwargs, 'login_info_id')
		loginInfo = CustomerExternalLoginInfo.objects.get(pk=loginInfoId)
		customerId = loginInfo.customer_id
		
		todayUtc = from_timestamp(utc_epoch(), utc).date()
		yesterdayUtc = todayUtc - timedelta(days=1)
		yearmonth = datetime.now().strftime("%Y%m")

		records = fetch_google_app_packages_name(loginInfo.refresh_token, loginInfo.gc_bucket_id, yearmonth)
		appInfos = [ai for ai in AppInfo.objects.filter(customer_id=customerId, platform='Google Play')]
		idToApp = {ai.app: ai for ai in appInfos}
		for record in records:
			productId = record
			if productId not in idToApp:
				print productId
				appInfo = fetcher.ANDROID_APP_INFO_FETCHER.fetch(productId,customerId,loginInfo)
	except Exception as e:
		raise self.retry(exc=e, countdown=exponential_backoff(self.request.retries))
