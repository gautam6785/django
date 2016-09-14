import logging, json
import re
import time
import os
import requests
import dashboard
import urllib
import urllib2
import cookielib
import datetime
import django.conf
from django.http import HttpResponse
from django.shortcuts import render, redirect, render_to_response
from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext
from django.contrib.auth.models import User
from django.contrib.auth import logout, login, authenticate
from django.contrib import messages
from django.core.cache import cache
from django import forms
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from string import split
from base64 import b64encode
from os import urandom
from celery import chain
from traceback import format_exc
from oauth2client.client import OAuth2WebServerFlow
from re import match
from urlparse import urlparse, urlsplit
#from pyicloud import PyiCloudService

from customers import ephemera, webdriverfactory
from customers.models import Customer, CustomerExternalLoginInfo
from customers.tasks import fetch_external_service_login_info
from customers.forms import *
from appinfo.models import AppInfo, AppScreenshot
from metrics.tasks.reporttasks import backfill_daily_sales_report_metrics
from core.timeutils import utc_epoch
from core.shared.lib.pyicloud import PyiCloudService
from core.oauth.constants import GSUTIL_CLIENT_ID, GSUTIL_CLIENT_NOTSOSECRET
from core.seleniumutils import click_through_to_new_page, submit_to_new_page
from core.gcs_oauth2_boto_plugin import oauth2_client

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from selenium.selenium import selenium 
from pyvirtualdisplay import Display
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

logger = logging.getLogger(__name__)

GOOGLE_ACCOUNTS_DOMAIN = 'accounts.google.com'
GOOGLE_DEV_CONSOLE_URL = 'https://console.developers.google.com/'

AUTH_URI = 'https://accounts.google.com/o/oauth2/auth'
TOKEN_URI = 'https://accounts.google.com/o/oauth2/token'
REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'
SCOPE_READ_ONLY = 'https://www.googleapis.com/auth/devstorage.read_only'

APPLE_CSRF_SCRIPT_URL = 'https://reportingitc2.apple.com/ligerService/owasp/csrf-guard.js'
APPLE_REPORTS_API_URL_BASE = 'https://reportingitc2.apple.com/api/reports?_='
APPLE_REPORTS_URL = 'https://reportingitc2.apple.com/reports.html'
APPLE_USERINFO_API_URL_BASE = 'https://reportingitc2.apple.com/api/user/info?_='
#APPLE_REPORTS_API_URL_BASE = 'https://itunesconnect.apple.com/itc/payments_and_financial_reports'
#APPLE_REPORTS_URL = 'https://itunesconnect.apple.com/itc/payments_and_financial_reports'
ITUNES_CONNECT_LOGIN_PAGE = 'https://itunesconnect.apple.com'


def itunes_and_google_account_lists(user):
    itunes_accounts = []
    google_play_accounts = []
    
    try:
        customer = Customer.objects.get(auth_user=user)
    except Customer.DoesNotExist:
        customer = None
    
    if customer is not None:
        connected_accounts = CustomerExternalLoginInfo.objects.filter(customer_id=customer.customer_id,
            is_active=True)
    
        for c in connected_accounts:
            copied_c = {}
            appinfo = AppInfo.objects.filter(customer_account_id=c.login_info_id)
            app_count = appinfo.count()
            
            app_icon = []
            for app in appinfo:
                icon = app.icon_url
                app_icon.append({'icon': icon})
                
            copied_c['icon'] = app_icon
            copied_c['id'] = c.login_info_id
            copied_c['app_count'] = app_count
            copied_c['username'] = c.username
            copied_c['external_service'] = c.external_service
            copied_c['creation_time'] = c.creation_time
            copied_c['latest_report'] = c.latest_report
            copied_c['display_name'] = c.display_name
            
            if c.external_service == 'iTunes Connect':
                itunes_accounts.append(copied_c)
            if c.external_service == 'Google Cloud':
                google_play_accounts.append(copied_c)
    return itunes_accounts, google_play_accounts

@require_POST
@login_required
def update_sales_reports_account(request):
    username = request.user.username
    form_info = json.loads(request.body)

    if 'platform' in form_info and 'username' in form_info and 'password' in form_info:       
        found = False
        
        try:
            customer = Customer.objects.get(auth_user=request.user)
        except Customer.DoesNotExist:
            customer = None
        
        if customer is not None:
            connected_accounts = CustomerExternalLoginInfo.objects.filter(customer_id=customer, is_active=True)
            for account in connected_accounts:
                if account.username == form_info['username'] and account.external_service == form_info['platform']:
                    # TODO(d-felix): Validate the new password before updating.
                    account.password = form_info['password']
                    account.display_name = form_info['display_name']
                    account.save()
                    found = True
                    kickoff_backfill(account, customer)
                    return HttpResponse(json.dumps({'message':'Password updated.'}), content_type='application/json')

        if not found:
            new_account = CustomerExternalLoginInfo(customer_id=customer,
                                                    username=form_info['username'],
                                                    password=form_info['password'],
                                                    external_service=form_info['platform'],
                                                    display_name=form_info['display_name'],
                                                    is_active=False,
                                                    step2_verification=False)
            new_account.save()
            # Note that account validation is slow and blocking.

            try:
                result = new_account.is_valid()

                if result['login'] == False:
                    return HttpResponse(json.dumps({"error": "Wrong username or password.", "login": False, "step2_verification": False}), content_type='application/json')
                elif result['login'] == True and result['step2_verification'] == True:
                    new_account.is_active = True
                    new_account.save()
                    request.session["login_info_id"] = new_account.login_info_id
                    #kickoff_backfill(new_account, customer)
                    return HttpResponse(json.dumps({"message": "Step2 Verfication is required","login": True, "step2_verification": True}), content_type='application/json')
                else:
                    new_account.is_active = True
                    new_account.step2_verification = True
                    new_account.save()
                    kickoff_backfill(new_account, customer)
                    return HttpResponse(json.dumps({}), content_type='application/json')
            except Exception:
                logger.warning('Attempted sales account sync failed for customer %s. Traceback: %s, ' %
                               (customer.customer_id, format_exc()))
                return HttpResponse(json.dumps({"error": "Something went wrong."}), content_type='application/json')

        return HttpResponse(json.dumps({"error":"NOT SET UP YET"}), content_type='application/json')


def kickoff_backfill(account, customer):
    # Generate a cache key that can be used to check on the progress of the backfill.
    doneToken = b64encode(urandom(20)).rstrip('==')
    ephemera.set_key(customer.customer_id, doneToken, account.external_service)
    #backfill_daily_sales_report_metrics.s(login_info_id=account.login_info_id,done_token=doneToken)
    backfill_tasks = chain(
        fetch_external_service_login_info.s(login_info_id=account.login_info_id),
        backfill_daily_sales_report_metrics.s(login_info_id=account.login_info_id,done_token=doneToken))
    backfill_tasks.apply_async()

def default_oauth2_client():
  cred_type=oauth2_client.CredTypes.OAUTH2_USER_ACCOUNT
  token_cache = oauth2_client.FileSystemTokenCache()

  return oauth2_client.OAuth2UserAccountClient(
      TOKEN_URI, GSUTIL_CLIENT_ID, GSUTIL_CLIENT_NOTSOSECRET, None,
      auth_uri=AUTH_URI, access_token_cache=token_cache,
      disable_ssl_certificate_validation=False,
      proxy_host=None, proxy_port=None, proxy_user=None, proxy_pass=None,
      ca_certs_file=None)

# 2step vefication.

@require_POST
@login_required
def get_2_step_verification_page(request):
    error, codeSource, phoneString = None, None, None

    loginInfoId = request.session["login_info_id"]
    loginInfo = CustomerExternalLoginInfo.objects.get(pk=loginInfoId)

    driver = webdriverfactory.phantom_js()
    driver.delete_all_cookies()
    driver.get(GOOGLE_DEV_CONSOLE_URL)

    loginForm = driver.find_element_by_id("gaia_loginform")
    loginForm.find_element_by_id("Email").send_keys(loginInfo.username)

    nextButton = loginForm.find_element_by_id("next")
    nextButton.click()

    wait = WebDriverWait(driver, 10)
    password_input = wait.until(EC.visibility_of_element_located((By.ID,'Passwd')))

    password_input.send_keys(loginInfo.password)
    signInButton = loginForm.find_element_by_id("signIn")
    click_through_to_new_page(signInButton, timeout_secs=10)

    googleTemplate = open(os.getcwd() + '/mobbo/templates/partials/verification-google-page.html', 'r').read()
    googleTemplate = googleTemplate.replace(u"{{username}}", loginInfo.username)

    challenge = driver.find_element_by_id("challenge")

    try:
        challenge.find_element_by_id("idvPreregisteredPhonePin")
        phoneElement = True
    except NoSuchElementException:
        phoneElement = False

    try:
        challenge.find_element_by_id("totpPin")
        appElement = True
    except NoSuchElementException:
        appElement = False

    try:
        driver.find_element_by_id("errorMsg")
        errorMsg = True
    except NoSuchElementException:
        errorMsg = False

    try:
        driver.find_element_by_class_name('H9T9of')
        warningMsg = True
    except NoSuchElementException:
        warningMsg = False

    if phoneElement:
        phoneForm = open(os.getcwd() + '/mobbo/templates/partials/verification-google-page-phone.html', 'r').read()
        googleTemplate = googleTemplate.replace(u"{{form}}", phoneForm)
        phoneString = challenge.find_element_by_class_name('DZNRQe').text
        googleTemplate = googleTemplate.replace(u"{{phoneString}}", phoneString)
        codeSource = u'phone'
    elif appElement:
        phoneApp = open(os.getcwd() + '/mobbo/templates/partials/verification-google-page-app.html', 'r').read()
        googleTemplate = googleTemplate.replace(u"{{form}}", phoneApp)
        codeSource = u'application'
    else:
        error = u"Not defined source"

    if errorMsg:
        errorString = u'<span class="Qx8Abe" id="errorMsg">%s</span>' % driver.find_element_by_id("errorMsg").text
        googleTemplate = googleTemplate.replace(u"{{errorMsg}}", errorString)
    else:
        googleTemplate = googleTemplate.replace(u"{{errorMsg}}", '')

    if warningMsg:
        warningString = u'<div class="H9T9of"><span class="y0GOlc">%s</span></div>' % driver.find_element_by_class_name('H9T9of').text
        googleTemplate = googleTemplate.replace(u"{{warningMsg}}", warningString)
    else:
        googleTemplate = googleTemplate.replace(u"{{warningMsg}}", '')

    return HttpResponse(json.dumps({"codeSource": codeSource, "error": error, 'template': googleTemplate}), content_type='application/json')


@require_POST
@login_required
def step2_verification(request):
    form_info = json.loads(request.body)
    #loginInfoId = form_info['login_info_id']
    loginInfoId = request.session["login_info_id"]
    smscode = form_info['smscode']
    codeSource = form_info['codeSource']

    # TODO(d-felix): Establish a high-priority celery queue for login validation
    # so that we don't have too many browsers in memory.
    # TODO(d-felix): Perform the lazy PhantomJS initialization at system startup.
    # Note that this webdriver is not threadsafe.

    driver = webdriverfactory.phantom_js()

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

    password_input.send_keys(loginInfo.password)
    signInButton = loginForm.find_element_by_id("signIn")
    click_through_to_new_page(signInButton, timeout_secs=10)

    #loginForm.find_element_by_id("Passwd").send_keys(loginInfo.password)
    #signInButton = loginForm.find_element_by_id("signIn")
    #click_through_to_new_page(signInButton, timeout_secs=10)

    #Fill sms form
    currentUrl = driver.current_url
    driver.get(currentUrl)
    challenge= driver.find_element_by_id("challenge")

    if codeSource == u"phone":
        challenge.find_element_by_id("idvPreregisteredPhonePin").send_keys(smscode)
    elif codeSource == u"application":
        challenge.find_element_by_id("totpPin").send_keys(smscode)

    submitButton = challenge.find_element_by_id("submit")
    click_through_to_new_page(submitButton, timeout_secs=10)

    try:
        driver.find_element_by_id("errorMsg")
        errorMsg = True
    except NoSuchElementException:
        errorMsg = False

    try:
        driver.find_element_by_class_name('H9T9of')
        warningMsg = True
    except NoSuchElementException:
        warningMsg = False

    if not errorMsg and not warningMsg:

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

        if urlWithBucketId != 'https://play.google.com/apps/publish/signup/':
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
            loginInfo.step2_verification = True
            loginInfo.save()
            return HttpResponse(json.dumps({'message': "Step2 verfication is successfully"}), content_type='application/json')
        else:
            # Save the refresh token and bucket ID to the database
            loginInfo.refresh_token = refreshToken
            loginInfo.step2_verification = True
            loginInfo.save()
            logger.error('Could not parse cloud storage bucket ID from url %s' % urlWithBucketId)
            return HttpResponse(json.dumps({'message':"Step2 verfication is successfully"}), content_type='application/json')

    else:
        googleTemplate = open(os.getcwd() + '/mobbo/templates/partials/verification-google-page.html', 'r').read()
        googleTemplate = googleTemplate.replace(u"{{username}}", loginInfo.username)

        if codeSource == u"phone":
            phoneForm = open(os.getcwd() + '/mobbo/templates/partials/verification-google-page-phone.html', 'r').read()
            googleTemplate = googleTemplate.replace(u"{{form}}", phoneForm)
            phoneString = driver.find_element_by_class_name('DZNRQe').text
            googleTemplate = googleTemplate.replace(u"{{phoneString}}", phoneString)
        elif codeSource == u"application":
            phoneApp = open(os.getcwd() + '/mobbo/templates/partials/verification-google-page-app.html', 'r').read()
            googleTemplate = googleTemplate.replace(u"{{form}}", phoneApp)

        if errorMsg:
            errorString = u'<span class="Qx8Abe" id="errorMsg">%s</span>' % driver.find_element_by_id("errorMsg").text
            googleTemplate = googleTemplate.replace(u"{{errorMsg}}", errorString)
        else:
            googleTemplate = googleTemplate.replace(u"{{errorMsg}}", '')

        if warningMsg:
            warningString = u'<div class="H9T9of"><span class="y0GOlc">%s</span></div>' % driver.find_element_by_class_name('H9T9of').text
            googleTemplate = googleTemplate.replace(u"{{warningMsg}}", warningString)
        else:
            googleTemplate = googleTemplate.replace(u"{{warningMsg}}", '')

        return HttpResponse(json.dumps({'error': "Wrong code", "template": googleTemplate}), content_type='application/json')

    return HttpResponse(json.dumps({'error':"sms code is expire please try again"}), content_type='application/json')


@require_POST
@login_required
def delete_sales_reports_account(request):
  # \todo remove saved reports?
  form_info = json.loads(request.body)
  if 'platform' in form_info and 'username' in form_info:
    customer = Customer.objects.get(auth_user=request.user)
    connected_accounts = CustomerExternalLoginInfo.objects.filter(customer_id=customer)
    foundAccount = None
    for account in connected_accounts:
      if account.username == form_info['username']:
        foundAccount = account
        break
    if foundAccount:
      foundAccount.is_active = False
      foundAccount.save()
      return HttpResponse(json.dumps({"success":True}), content_type='application/json')
    return HttpResponse(json.dumps({"error":"Account not found"}), content_type='application/json')



@login_required
def itunes_login(request):
	username = ''
	password = ''
	
	api = PyiCloudService(username, password)
	
	if(api.results['login']):
		print 'Successfully Login'
	else:
		print 'Login Credentials incorrect'
	
	
	logger.info(api.results['login'])
	print api
	
	
	"""
	driver = webdriver.Firefox()
	#driver = webdriverfactory.phantom_js()
	driver.delete_all_cookies()
	driver.get("https://itunesconnect.apple.com")
	
	wait = WebDriverWait(driver, 20)
	frame = wait.until(EC.visibility_of_element_located((By.ID,'authFrame')))      
	driver.switch_to.frame(driver.find_element_by_id("authFrame"))
	appleId_input = wait.until(EC.visibility_of_element_located((By.ID,'appleId')))
	appleId_input.send_keys(username)
	password_input = wait.until(EC.visibility_of_element_located((By.ID,'pwd')))
	password_input.send_keys(password)
	signInButton = driver.find_element_by_id("sign-in")
	#click_through_to_new_page(signInButton, timeout_secs=10)
	signInButton.click()
	time.sleep(10)

	#driver.implicitly_wait(10)
	
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
	
	# Retrieve the user report information using the private API.
	userInfoUrl = APPLE_USERINFO_API_URL_BASE + str(long(time.time() * 1000))
	response1 = requests.get(userInfoUrl, cookies=cookies, headers=headers)
	logger.info(response1.content)
	

	# Retrieve the report information using the private API.
	reportInfoUrl = APPLE_REPORTS_API_URL_BASE + str(long(time.time() * 1000))
	response = requests.get(reportInfoUrl, cookies=cookies, headers=headers)
	
	#logger.info(response.content)
	
	if not response.content:
		raise ValueError('Content missing from apple reports API response for login_info_id')
	
	
	reportInfo = response.json()
	
	try:
		entry = reportInfo['contents'][0] if 'contents' in reportInfo else reportInfo
		vendorIdStr = entry['reports'][0]['vendors'][0]['id']
	except Exception as e:
		raise ValueError('Encountered unrecognized apple reports API response: %s. ' +
			'Failed with message %s' % (reportInfo, e.message))
	
	vendorId = long(vendorIdStr)
	
	logger.info(vendorId)
	"""
	return render(request, 'download/test.html')


@login_required
def google_login(request):
    #username = ''
    #password = ''
    loginInfoId = 16
    #driver = webdriver.Firefox()
    driver = webdriverfactory.phantom_js()
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

    password_input.send_keys(loginInfo.password)
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
    
    return render(request, 'download/test.html')
