#import django_filters
from django.db import models
from core.customfields import BigAutoField, BigIntegerField
from core.models import TimestampedModel
from customers.models import Customer, CustomerExternalLoginInfo
from django.utils import timezone

class PlatformType(TimestampedModel):
  platform_type_id = models.AutoField(primary_key=True)

  ANDROID = 'Android'
  IOS = 'iOS'
  WEB = 'Web'
  PLATFORM_TYPE_STR_CHOICES = (
    (ANDROID, 'Android'),
    (IOS, 'iOS'),
    (WEB, 'Web'),
  )
  platform_type_str = models.CharField(choices=PLATFORM_TYPE_STR_CHOICES,
      max_length=255, unique=True)
  description = models.CharField(max_length=512)

  class Meta:
    db_table = 'platform_types'
    
    
class AppInfo(models.Model):
  app_info_id = BigAutoField(primary_key=True)
  customer_id = models.ForeignKey(Customer, db_column="customer_id", null=True, db_index=True)
  customer_account_id = models.ForeignKey(CustomerExternalLoginInfo, db_column="customer_account_id", null=True, db_index=True)
  app = models.CharField(max_length=256, db_index=True)
  name = models.CharField(max_length=256, null=True)
  sku = models.CharField(max_length=256, null=True)
  identifier = BigIntegerField(null=True)
  artist_id = BigIntegerField(null=True)
  platform = models.CharField(max_length=256)
  platform_type_id = models.ForeignKey(PlatformType, db_column="platform_type_id", null=True, db_index=True)
  category = models.CharField(max_length=256, null=True)
  price = models.DecimalField(max_digits=30, decimal_places=10, null=True, default=0)
  formatted_price = models.CharField(max_length=256, null=True)
  currency = models.CharField(max_length=256, null=True)
  description = models.TextField(null=True)
  icon_url = models.CharField(max_length=4096, null=True)
  rating = models.CharField(max_length=256, null=True)
  rating1 = BigIntegerField(null=True,default=0)
  rating2 = BigIntegerField(null=True,default=0)
  rating3 = BigIntegerField(null=True,default=0)
  rating4 = BigIntegerField(null=True,default=0)
  rating5 = BigIntegerField(null=True,default=0)
  version = models.CharField(max_length=256, null=True)
  content_rating = models.CharField(max_length=256, null=True)
  size = models.CharField(max_length=256, null=True)
  developer = models.CharField(max_length=256, null=True)
  developer_email = models.CharField(max_length=256, null=True)
  developer_website = models.CharField(max_length=256, null=True)
  install = models.CharField(max_length=256, null=True)
  total_downloads = models.BigIntegerField(null=True, default=0)
  total_revenue = models.DecimalField(max_digits=30, decimal_places=10, null=True, default=0)
  iap_revenue = models.DecimalField(max_digits=30, decimal_places=10, null=True, default=0)
  ad_revenue = models.DecimalField(max_digits=30, decimal_places=10, null=True, default=0)
  has_iap = BigIntegerField(null=True, default=0)
  iap_min = models.DecimalField(max_digits=30, decimal_places=10, null=True, default=0)
  iap_max = models.DecimalField(max_digits=30, decimal_places=10, null=True, default=0)
  release_date = models.DateField(null=True)
  fetch_time = models.DateTimeField(auto_now_add=True, db_index=True)
  
  class Meta:
    db_table = 'app_info'


class AppScreenshot(TimestampedModel):
  #creation_time = models.DateTimeField(auto_now_add=True)
  #last_modified = models.DateTimeField(auto_now=True)
  app_screenshot_id = BigAutoField(primary_key=True)
  screenshots = models.CharField(max_length=4096)
  app_info_id = models.ForeignKey(AppInfo, db_column="app_info_id", null=True)

  class Meta:
    db_table = 'app_screenshots'

class Currency(models.Model):
  iso_code = models.CharField(primary_key=True, max_length=3)
  symbol = models.CharField(max_length=3)
  uni_code = models.CharField(max_length=8)
  position = models.CharField(max_length=6)
  comments = models.CharField(max_length=255)
    
  class Meta:
    db_table = 'currencies'
    verbose_name = 'currency'
    verbose_name_plural = 'currencies'
