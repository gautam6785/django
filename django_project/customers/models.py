import logging
import re
from core.customfields import EncryptedCharField
from core.models import TimestampedModel
from core.seleniumutils import click_through_to_new_page, submit_to_new_page
from customers import webdriverfactory
from django.conf import settings
from django.db import models
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait
from urlparse import urlparse, urlsplit
from core.shared.lib.pyicloud import PyiCloudService
from selenium import webdriver

GOOGLE_ACCOUNTS_DOMAIN = 'accounts.google.com'
GOOGLE_DEV_CONSOLE_URL = 'https://console.developers.google.com/'

ITC_LOGIN_PAGE = 'https://itunesconnect.apple.com'

logger = logging.getLogger(__name__)


class Customer(TimestampedModel):
    customer_id = models.AutoField(primary_key=True)
    auth_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, db_column="auth_user")
    name = models.CharField(max_length=256, null=True)
    timezone = models.CharField(max_length=256, default='America/Los_Angeles')

    class Meta:
        db_table = 'customers'
    
    
class CustomerExternalLoginInfo(TimestampedModel):
    login_info_id = models.AutoField(primary_key=True)
    customer_id = models.ForeignKey(Customer, db_column="customer_id", null=True)
    username = EncryptedCharField(max_length=256)
    password = EncryptedCharField(max_length=256)
    apple_vendor_id = models.BigIntegerField(null=True, db_index=True)
    refresh_token = EncryptedCharField(max_length=256, null=True)
    gc_bucket_id = models.CharField(max_length=256, null=True)
    is_active = models.BooleanField(default=True)
    step2_verification = models.BooleanField(default=True)
    display_name = models.CharField(max_length=256, null=True)
    latest_report = models.DateTimeField(null=True)

    GOOGLE_CLOUD = 'Google Cloud'
    ITUNES_CONNECT = 'iTunes Connect'
    EXTERNAL_SERVICE_CHOICES = (
        (GOOGLE_CLOUD, 'Google Cloud'),
        (ITUNES_CONNECT, 'iTunes Connect'),
    )
    external_service = models.CharField(choices=EXTERNAL_SERVICE_CHOICES, max_length=256,
        db_index=True)

    def is_valid(self):
        # TODO(d-felix): Establish a high-priority celery queue for login validation
        # so that we don't have too many browsers in memory.
        # TODO(d-felix): Perform the lazy PhantomJS initialization at system startup.
        # Note that this webdriver is not threadsafe.
        driver = webdriverfactory.phantom_js()
        #driver = webdriver.Firefox()
        driver.delete_all_cookies()

        if self.external_service == self.GOOGLE_CLOUD:
            logger.warning('Start google auto login process')
            driver.get(GOOGLE_DEV_CONSOLE_URL)

            # The Email field may be prepopulated and read-only.
            # TODO(d-felix): This undesirable behavior is caused by our PhantomJS
            # singleton maintaining some state between uses despite cookie deletion.
            # Investigate the possibility of a faster workaround.
            changeAccountLinks = driver.find_elements_by_id("account-chooser-link")
            if changeAccountLinks:
                click_through_to_new_page(changeAccountLinks[0], timeout_secs=10)
                addAccountLink = driver.find_element_by_id("account-chooser-add-account")
                click_through_to_new_page(addAccountLink, timeout_secs=10)

            loginForm = driver.find_element_by_id("gaia_loginform")
            loginForm.find_element_by_id("Email").send_keys(self.username)

            nextButton = loginForm.find_element_by_id("next")
            nextButton.click()

            wait = WebDriverWait(driver, 10)
            password_input = wait.until(expected_conditions.visibility_of_element_located((By.ID,'Passwd')))

            password_input.send_keys(self.password)
            signInButton = loginForm.find_element_by_id("signIn")
            click_through_to_new_page(signInButton, timeout_secs=10)

            currentUrl = driver.current_url
            parsed = urlparse(currentUrl)
            domain = parsed.netloc
            path = parsed.path
            fragment = parsed.fragment
            query = parsed.query

            # driver.switch_to().frame("lv-frame")

            # """
            if domain == GOOGLE_ACCOUNTS_DOMAIN and path == "/ServiceLoginAuth" and fragment is not None:
                results = {'login': False, 'step2_verification': False}
                logger.warning('Failed to verify Google Cloud login for customer %s. Page source: %s' %
                    (self.customer_id.customer_id, driver.page_source))
            elif domain == GOOGLE_ACCOUNTS_DOMAIN and path != "/ServiceLoginAuth" and fragment in [None, '']:
                results = {'login': True, 'step2_verification': True}
                logger.warning('Step2 verfication is required for Google Cloud login for customer %s. Page source: %s' %
                    (self.customer_id.customer_id, driver.page_source))
            else:
                results = {'login': True, 'step2_verification': False}
                logger.info('Treating google login as valid since form submission redirected to %s' % domain)

            return results
            # """

            """
            domain = re.match(r'^https?://([^/]+)/.*', currentUrl).group(1)
            if domain == GOOGLE_ACCOUNTS_DOMAIN:
            logger.warning('Failed to verify Google Cloud login for customer %s. Page source: %s' %
                (self.customer_id.customer_id, driver.page_source))
            return False
            logger.info('Treating google login as valid since form submission redirected to %s' % domain)
            return True
            """
        elif self.external_service == self.ITUNES_CONNECT:
            api = PyiCloudService(self.username, self.password)
            if(api.results['login']):
                results = {'login': True, 'step2_verification': False}
                logger.info('Successfully login itunesconnect.apple.com')
            else:
                results = {'login': False, 'step2_verification': False}
                logger.info('Apple Id or Password not found in itunesconnect.apple.com')
            
            return results

    class Meta:
        db_table = 'customer_external_login_info'


