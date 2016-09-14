from django.db import models
from core.customfields import BigAutoField, BigForeignKey
from core.db.constants import DEFAULT_DECIMAL_PRECISION
from core.models import TimestampedModel
from customers.models import Customer, CustomerExternalLoginInfo
from metrics.constants import SESSION_START_EVENT_IDS
from localization.models import Country
# Create your models here.

# Apple product type identifier groupings
APP_BUNDLE_RECORDS = ['1-B']
FREE_OR_PAID_APP_RECORDS = ['1', '1F', '1T', 'F1']
PAID_APP_RECORDS = ['1E', '1EP', '1EU']
UPDATE_RECORDS = ['7', '7F', '7T', 'F7']
IN_APP_PURCHASE_RECORDS = ['IA1', 'IA9', 'IAC', 'IAY', 'FI1']
RECURRENCE_RECORDS = ['IA9', 'IAC', 'IAY']

class AppleReportRecord(TimestampedModel):
  record_id = BigAutoField(primary_key=True)
  customer_id = models.ForeignKey(Customer, db_column="customer_id")
  apple_identifier = models.BigIntegerField(db_index=True)
  provider = models.CharField(max_length=10)
  provider_country = models.CharField(max_length=10)
  sku = models.CharField(max_length=100)
  developer = models.CharField(max_length=4000, null=True)
  title = models.CharField(max_length=600)
  version = models.CharField(max_length=100, null=True)
  product_type_identifier = models.CharField(max_length=20)
  units = models.DecimalField(max_digits=20, decimal_places=2)
  developer_proceeds = models.DecimalField(max_digits=20, decimal_places=2)
  developer_proceeds_usd = models.DecimalField(max_digits=30,
      decimal_places=DEFAULT_DECIMAL_PRECISION)
  begin_date = models.DateField()
  end_date = models.DateField()
  customer_currency = models.CharField(max_length=10)
  #country_code = models.ForeignKey(Country, db_column="country_code", to_field='alpha2', related_name="countries")
  country_code = models.CharField(max_length=256, null=True)
  currency_of_proceeds = models.CharField(max_length=10)
  customer_price = models.DecimalField(max_digits=20, decimal_places=2)
  promo_code = models.CharField(max_length=10, null=True)
  parent_identifier = models.CharField(max_length=100, null=True)
  subscription = models.CharField(max_length=10, null=True)
  period = models.CharField(max_length=30, null=True)
  category = models.CharField(max_length=50)
  cmb = models.CharField(max_length=5, null=True)
  device = models.CharField(max_length=600, null=True)
  supported_platforms = models.CharField(max_length=600, null=True)

  def is_app(self):
    return self.product_type_identifier in FREE_OR_PAID_APP_RECORDS + PAID_APP_RECORDS + \
        UPDATE_RECORDS

  def is_app_bundle(self):
    return self.product_type_identifier in APP_BUNDLE_RECORDS

  def is_in_app_purchase(self):
    return self.product_type_identifier in IN_APP_PURCHASE_RECORDS

  def is_recurrence(self):
    return self.product_type_identifier in RECURRENCE_RECORDS

  def is_update(self):
    return self.product_type_identifier in UPDATE_RECORDS

  def is_download(self):
    return (self.product_type_identifier in FREE_OR_PAID_APP_RECORDS + PAID_APP_RECORDS +
        APP_BUNDLE_RECORDS) and self.units >= 0

  def is_refund(self):
    return self.units < 0

  class Meta:
    db_table = 'apple_report_records'

class GoogleReportRecord(TimestampedModel):
  record_id = BigAutoField(primary_key=True)
  customer_id = models.ForeignKey(Customer, db_column="customer_id")
  order_number = models.CharField(db_index=True, max_length=255)
  charged_date = models.DateField()
  charged_time = models.DateTimeField()
  financial_status = models.CharField(max_length=100)
  device_model = models.CharField(max_length=100, null=True)
  product_title = models.CharField(max_length=600)
  product_id = models.CharField(max_length=256, db_index=True)
  product_type = models.CharField(max_length=100)
  sku_id = models.CharField(max_length=256, null=True)
  sale_currency = models.CharField(max_length=10)
  item_price = models.DecimalField(max_digits=30, decimal_places=DEFAULT_DECIMAL_PRECISION)
  taxes = models.DecimalField(max_digits=30, decimal_places=DEFAULT_DECIMAL_PRECISION)
  charged_amount = models.DecimalField(max_digits=30, decimal_places=DEFAULT_DECIMAL_PRECISION)
  developer_proceeds = models.DecimalField(max_digits=30,
      decimal_places=DEFAULT_DECIMAL_PRECISION)
  developer_proceeds_usd = models.DecimalField(max_digits=30,
      decimal_places=DEFAULT_DECIMAL_PRECISION)
  buyer_city = models.CharField(max_length=256, null=True)
  buyer_state = models.CharField(max_length=256, null=True)
  buyer_postal_code = models.CharField(max_length=256, null=True)
  buyer_country = models.CharField(max_length=256, null=True)
  #buyer_country = models.ForeignKey(Country, db_column="buyer_country", to_field='alpha2', related_name="google_countries")
  timestamp = models.CharField(max_length=256, null=True)
  google_fee = models.DecimalField(max_digits=30, decimal_places=DEFAULT_DECIMAL_PRECISION, null=True)
  currency_conversion_rate = models.DecimalField(max_digits=30, decimal_places=DEFAULT_DECIMAL_PRECISION, null=True)
  amount_merchant_currency = models.DecimalField(max_digits=30, decimal_places=DEFAULT_DECIMAL_PRECISION, null=True)
  merchant_currency = models.CharField(max_length=10, null=True)

  def is_app(self):
    return False if self.sku_id else True

  def is_recurrence(self):
    return self.product_type == 'subscription'

  def payment_direction(self):
    return -1 if (self.financial_status == 'Refund' or self.charged_amount < 0) else 1

  def is_download(self):
    return self.is_app() and self.financial_status == 'Charged'

  def is_refund(self):
    return self.financial_status == 'Refund'

  class Meta:
    db_table = 'google_report_records'


class GoogleInstallationReportRecord(TimestampedModel):
  record_id = BigAutoField(serialize=False, primary_key=True)
  customer_id = models.ForeignKey(Customer, db_column="customer_id")
  date = models.DateField()
  package_name = models.CharField(max_length=256, db_index=True)
  country = models.CharField(max_length=256, null=True)
  current_device_installs = models.IntegerField()
  daily_device_installs = models.IntegerField()
  daily_device_uninstalls = models.IntegerField()
  daily_device_upgrades = models.IntegerField()
  current_user_installs = models.IntegerField()
  total_user_installs = models.IntegerField()
  daily_user_installs = models.IntegerField()
  daily_user_uninstalls = models.IntegerField()

  class Meta:
    db_table = 'google_installation_report_records'
