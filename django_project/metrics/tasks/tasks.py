from __future__ import absolute_import

from celery import group, task
from celery.utils.log import get_task_logger
from core.celeryutils import exponential_backoff
from core.timeutils import convert_tz, deserialize_unaware, display, serialize_unaware, today
from customers.models import Customer
from datetime import timedelta
from decimal import Decimal
from django.core import serializers
from django.db import connection, transaction
from ingestor.models import App, ChannelProduct, CustomerLabel, PlatformApp
from metrics.constants import ANDROID_DEVELOPER_REVENUE_SHARE, IOS_DEVELOPER_REVENUE_SHARE, MAU_DURATION_DAYS, SESSION_START_EVENT_IDS
from metrics.models import DailyCustomerMetrics, DailyLabelMetrics, DailyPlatformAppMetrics, DailyProductMetrics
from pytz import timezone, utc

SESSION_START_EVENT_IDS_TUPLE = tuple(SESSION_START_EVENT_IDS)

logger = get_task_logger(__name__)

# The maximum number of times a task from this module may be retried.
_MAX_RETRIES = 5

# Generates DAU metrics for a single platform_app.
_SINGLE_PLATFORM_APP_DAU_QUERY = """
  SELECT
    subquery.date date,
    COUNT(*) dau
  FROM (
    SELECT DISTINCT
      (time AT TIME ZONE %s)::date date,
      scriber_id
    FROM
      user_events
    WHERE
      platform_app_id = %s
      AND time >= %s
      AND time < %s
      AND event_type IN (2, 3, 5, 9)
  ) subquery
  GROUP BY 1;
  """

# Generates DAU metrics for a single platform_app using the customer-provided customer_user_id
# value to identify end users.
_SINGLE_PLATFORM_APP_USER_ID_DAU_QUERY = """
  SELECT
    subquery.date date,
    COUNT(*) dau
  FROM (
    SELECT DISTINCT
      (e.time AT TIME ZONE %s)::date date,
      (CASE WHEN (u.customer_user_id = '') THEN CAST(u.scriber_id AS varchar) ELSE u.customer_user_id END) user_id
    FROM
      user_events e JOIN users u ON e.scriber_id = u.scriber_id
    WHERE
      e.platform_app_id = %s
      AND e.time >= %s
      AND e.time < %s
      AND e.event_type IN (2, 3, 5, 9)
  ) subquery
  GROUP BY 1;
  """

# Generates session metrics for a single platform_app using the customer-provided customer_user_id
# value to identify end users.
# Each customer_user_id can contribute at most one session start per second.
_SINGLE_PLATFORM_APP_USER_ID_SESSIONS_QUERY = """
  SELECT
    (subquery.local_time_secs)::date date,
    COUNT(*) sessions
  FROM (
    SELECT DISTINCT
      date_trunc('second', e.time) AT TIME ZONE %s AS local_time_secs,
      (CASE WHEN (u.customer_user_id = '') THEN CAST(u.scriber_id AS varchar) ELSE u.customer_user_id END) user_id
    FROM
      user_events e JOIN users u ON e.scriber_id = u.scriber_id
    WHERE
      e.platform_app_id = %s
      AND e.time >= %s
      AND e.time < %s
      AND e.event_type IN %s
  ) subquery
  GROUP BY 1;
  """

# Calculates the number of active users over the specified time period.
_SINGLE_PLATFORM_APP_ACTIVES_QUERY = """
  SELECT
    COUNT(*) actives
  FROM (
    SELECT DISTINCT
      scriber_id
    FROM
      user_events
    WHERE
      platform_app_id = %s
      AND time >= %s
      AND time < %s
      AND event_type IN (2, 3, 5, 9)
  ) subquery;
  """

# Calculates the number of active users over the specified time period using the customer-provided
# customer_user_id value to identify end users.
_SINGLE_PLATFORM_APP_USER_ID_ACTIVES_QUERY = """
  SELECT
    COUNT(*) actives
  FROM (
    SELECT DISTINCT
      (CASE WHEN (u.customer_user_id = '') THEN CAST(u.scriber_id AS varchar) ELSE u.customer_user_id END) user_id
    FROM
      user_events e JOIN users u ON e.scriber_id = u.scriber_id
    WHERE
      e.platform_app_id = %s
      AND e.time >= %s
      AND e.time < %s
      AND e.event_type IN (2, 3, 5, 9)
  ) subquery;
  """

# Generates DAU metrics for a single customer.
_SINGLE_CUSTOMER_DAU_QUERY = """
  SELECT
    subquery.date date,
    COUNT(*) dau
  FROM (
    SELECT DISTINCT
      (u.time AT TIME ZONE %s)::date date,
      u.scriber_id
    FROM
      customers c JOIN apps a ON c.customer_id = a.customer_id
      JOIN platform_apps p ON a.app_id = p.app_id
      JOIN user_events u ON p.platform_app_id = u.platform_app_id
    WHERE
      c.customer_id = %s
      AND u.time >= %s
      AND u.time < %s
      AND u.event_type IN (2, 3, 5, 9)
  ) subquery
  GROUP BY 1;
  """

# Generates DAU metrics for a single customer using the customer-provided customer_user_id value to
# identify end users.
_SINGLE_CUSTOMER_USER_ID_DAU_QUERY = """
  SELECT
    subquery.date date,
    COUNT(*) dau
  FROM (
    SELECT DISTINCT
      (e.time AT TIME ZONE %s)::date date,
      (CASE WHEN (u.customer_user_id = '') THEN CAST(u.scriber_id AS varchar) ELSE u.customer_user_id END) user_id
    FROM
      customers c JOIN apps a ON c.customer_id = a.customer_id
      JOIN platform_apps p ON a.app_id = p.app_id
      JOIN user_events e ON p.platform_app_id = e.platform_app_id
      JOIN users u ON e.scriber_id = u.scriber_id
    WHERE
      c.customer_id = %s
      AND e.time >= %s
      AND e.time < %s
      AND e.event_type IN (2, 3, 5, 9)
  ) subquery
  GROUP BY 1;
  """

# Calculates a customer's number of active users over the specified time period.
_SINGLE_CUSTOMER_ACTIVES_QUERY = """
  SELECT
    COUNT(*) actives
  FROM (
    SELECT DISTINCT
      u.scriber_id
    FROM
      customers c JOIN apps a ON c.customer_id = a.customer_id
      JOIN platform_apps p ON a.app_id = p.app_id
      JOIN user_events u ON p.platform_app_id = u.platform_app_id
    WHERE
      c.customer_id = %s
      AND u.time >= %s
      AND u.time < %s
      AND u.event_type IN (2, 3, 5, 9)
  ) subquery;
  """

# Calculates a customer's number of active users over the specified time period using the
# customer-provided customer_user_id value to identify end users.
_SINGLE_CUSTOMER_USER_ID_ACTIVES_QUERY = """
  SELECT
    COUNT(*) actives
  FROM (
    SELECT DISTINCT
      (CASE WHEN (u.customer_user_id = '') THEN CAST(u.scriber_id AS varchar) ELSE u.customer_user_id END) user_id
    FROM
      customers c JOIN apps a ON c.customer_id = a.customer_id
      JOIN platform_apps p ON a.app_id = p.app_id
      JOIN user_events e ON p.platform_app_id = e.platform_app_id
      JOIN users u ON e.scriber_id = u.scriber_id
    WHERE
      c.customer_id = %s
      AND e.time >= %s
      AND e.time < %s
      AND e.event_type IN (2, 3, 5, 9)
  ) subquery;
  """

# Generates revenue metrics for a single product.
_SINGLE_PRODUCT_DAILY_REVENUE_QUERY = """
  SELECT
    u.channel_product_id,
    (u.time AT TIME ZONE %s)::date date,
    SUM(CASE WHEN (u.amt_usd_micros IS NOT NULL) THEN u.amt_usd_micros ELSE cp.amt_usd_micros END) revenueUsdMicros,
    SUM(CASE WHEN (cp.is_recurrence) THEN (CASE WHEN (u.amt_usd_micros IS NOT NULL) THEN u.amt_usd_micros ELSE cp.amt_usd_micros END) ELSE 0 END) recurringRevenueUsdMicros
  FROM
    customers c JOIN products p ON c.customer_id = p.customer_id
    JOIN channel_products cp ON p.product_id = cp.product_id
    LEFT JOIN user_purchases u ON cp.channel_product_id = u.channel_product_id 
  WHERE
    c.customer_id = %s
    AND u.time >= %s
    AND u.time < %s
    AND u.master_purchase_id IS NULL
  GROUP BY 1, 2;
  """

# Generates daily label-related metrics for a single app over the specified time period.
_SINGLE_APP_LABEL_QUERY = """
  SELECT
    cl.customer_label_id customer_label_id,
    (ue.time AT TIME ZONE %s)::date date,
    COUNT(*) count
  FROM
    user_events ue JOIN customer_labels cl ON ue.customer_label_id = cl.customer_label_id
  WHERE
    ue.platform_app_id = %s
    AND ue.event_type = 9
    AND ue.time >= %s
    AND ue.time < %s
  GROUP BY 1, 2;
  """

def _revenue_share(platformStr):
  if platformStr == 'Android':
    return ANDROID_DEVELOPER_REVENUE_SHARE
  elif platformStr == 'iOS':
    return IOS_DEVELOPER_REVENUE_SHARE
  else:
    return Decimal('1.0')

# TODO(d-felix): Make this task accept date d and timezone tz arguments. Subsequently, only create
# daily_metrics tasks for a customer c if, for instance, (d, 12:00AM, tz) and (d-1, 11:00PM, tz)
# resolve to different dates in c's timezone.
@task(max_retries=_MAX_RETRIES, ignore_result=True, bind=True)
def daily_metrics_kickoff(self):
  try:
    taskList = []
    for c in Customer.objects.all():
      todayForCustomer = today(timezone(c.timezone))
      yesterdayForCustomer = todayForCustomer - timedelta(days=1)
      yesterdayForCustomerStr = serialize_unaware(yesterdayForCustomer)
      taskList.append(daily_metrics.s(c.customer_id, yesterdayForCustomerStr))

    kickoff = group(taskList)
    kickoff.apply_async()
  except Exception as e:
    # Treat all exceptions as transient errors and retry.
    raise self.retry(exc=e, countdown=exponential_backoff(self.request.retries))


# Generates daily metrics for a single customer
# TODO(d-felix): Investigate retry behavior and how subtask failures resolve to task failures.
@task(max_retries=_MAX_RETRIES, ignore_result=True, bind=True)
def daily_metrics(self, customerId, dateStr):
  try:
    customer = Customer.objects.get(pk=customerId)

    # TODO(d-felix): Chain-ify the three asynchronous invocations in this task.
    daily_customer_metrics.delay(customerId, dateStr)
    daily_product_metrics.delay(customerId, dateStr)

    # Note that joining platform_apps with apps automatically excludes inactive app groupings.
    platformApps = PlatformApp.objects.filter(app_id__customer_id=customer)
    pGroup = group(daily_platform_app_metrics.s(customerId, dateStr, p.platform_app_id)
        for p in platformApps)
    pGroup.apply_async()

    lGroup = group(daily_label_metrics.s(customerId, dateStr, p.platform_app_id)
        for p in platformApps)
    lGroup.apply_async()

  except Exception as e:
    # Treat all exceptions as transient errors and retry.
    e.message = 'Daily metrics job for customer %s failed with error message: %s' % \
        (customerId, e.message)
    raise self.retry(exc=e, countdown=exponential_backoff(self.request.retries))


# Generates customer-specific non-additive metrics such as DAU and MAU.
@task(max_retries=_MAX_RETRIES, ignore_result=True, bind=True)
def daily_customer_metrics(self, customerId, dateStr):
  try:
    customer = Customer.objects.get(pk=customerId)
    customerTz = timezone(customer.timezone)

    # Calculate the start and end times of the analysis period.
    # The end date is the first date not included in the analysis period.
    # The end time is 12:00AM in the customer's timezone on the end date, expressed in UTC time.
    endTimeUnaware = deserialize_unaware(dateStr) + timedelta(days=1)
    endTime = convert_tz(endTimeUnaware, customerTz, timezone('UTC'))
    endTimeStr = display(endTime)
    endDate = endTimeUnaware.date()
    startTimeUnaware = endTimeUnaware - timedelta(days=1)
    startTime = convert_tz(startTimeUnaware, customerTz, timezone('UTC'))
    startTimeStr = display(startTime)
    startDate = startTimeUnaware.date()

    # Calculate the start time of the MAU analysis period.
    mauStartTimeUnaware = endTimeUnaware - timedelta(days=MAU_DURATION_DAYS)
    mauStartTime = convert_tz(mauStartTimeUnaware, customerTz, timezone('UTC'))
    mauStartTimeStr = display(mauStartTime)

    # The date assigned to an MAU calculation spanning the closed date interval
    # [startDate - timedelta(days=MAU_DURATION_DAYS-1), startDate]
    mauPersistDate = startDate

    # Build a dictionary of instances to save.
    metricsDict = {}

    # Prepopulate the dictionary with empty records
    for delta in range((endDate - startDate).days):
      date = startDate + timedelta(days=delta)
      key = date
      metricsDict[key] = DailyCustomerMetrics(customer_id=customer, date=date, dau=0, mau=0)

    # Fetch any existing metrics records that would need to be updated instead of inserted.
    # Note that the pair (customer, date) is unique for the DailyCustomerMetrics table.
    existingMetrics = DailyCustomerMetrics.objects.filter(customer_id=customer,
        date__gte=startDate, date__lt=endDate)

    # Update the dictionary with existing metrics entries, but zero out the metrics that
    # we intend to overwrite.
    for metric in existingMetrics:
      key = metric.date
      metric.dau = 0
      metric.mau = 0
      metricsDict[key] = metric

    # Execute the DAU query and update the dictionary.
    cursor = connection.cursor()
    cursor.execute(_SINGLE_CUSTOMER_USER_ID_DAU_QUERY,
        [customer.timezone, customerId, startTimeStr, endTimeStr])
    for record in cursor.fetchall():
      key = record[0]
      if key in metricsDict:
        metricsDict[key].dau = record[1] if record[1] is not None else 0

    # Execute the MAU query and update the dictionary.
    cursor.execute(_SINGLE_CUSTOMER_USER_ID_ACTIVES_QUERY,
        [customerId, mauStartTimeStr, endTimeStr])
    for record in cursor.fetchall():
      key = mauPersistDate
      if key in metricsDict:
        metricsDict[key].mau = record[0] if record[0] is not None else 0

    cursor.close()

    # Write results to the database
    with transaction.atomic():
      for key in metricsDict:
        metricsDict[key].save()

  except Exception as e:
    # Treat all exceptions as transient errors and retry.
    e.message = 'Daily customer metrics job for customer %s failed with error message: %s' % \
        (customerId, e.message)
    raise self.retry(exc=e, countdown=exponential_backoff(self.request.retries))


# Generates app-specific non-additive metrics such as DAU and MAU.
@task(max_retries=_MAX_RETRIES, ignore_result=True, bind=True)
def daily_platform_app_metrics(self, customerId, dateStr, platformAppId):
  try:
    customer = Customer.objects.get(pk=customerId)
    customerTz = timezone(customer.timezone)
    platformApp = PlatformApp.objects.get(pk=platformAppId)

    # Calculate the start and end times of the analysis period.
    # The end date is the first date not included in the analysis period.
    # The end time is 12:00AM in the customer's timezone on the end date, expressed in UTC time.
    endTimeUnaware = deserialize_unaware(dateStr) + timedelta(days=1)
    endTime = convert_tz(endTimeUnaware, customerTz, timezone('UTC'))
    endTimeStr = display(endTime)
    endDate = endTimeUnaware.date()
    startTimeUnaware = endTimeUnaware - timedelta(days=1)
    startTime = convert_tz(startTimeUnaware, customerTz, timezone('UTC'))
    startTimeStr = display(startTime)
    startDate = startTimeUnaware.date()

    # Calculate the start time of the MAU analysis period.
    mauStartTimeUnaware = endTimeUnaware - timedelta(days=MAU_DURATION_DAYS)
    mauStartTime = convert_tz(mauStartTimeUnaware, customerTz, timezone('UTC'))
    mauStartTimeStr = display(mauStartTime)

    # The date assigned to an MAU calculation spanning the closed date interval
    # [startDate - timedelta(days=MAU_DURATION_DAYS-1), startDate]
    mauPersistDate = startDate

    # Build a dictionary of instances to save.
    metricsDict = {}

    # Prepopulate the dictionary with empty records
    for delta in range((endDate - startDate).days):
      date = startDate + timedelta(days=delta)
      key = date
      metricsDict[key] = DailyPlatformAppMetrics(customer_id=customer,
          platform_app_id=platformApp, date=date, dau=0, mau=0, sessions=0)

    # Fetch any existing metrics records that would need to be updated instead of inserted.
    # Note that the triple (customer, platformApp, date) is unique for the
    # DailyPlatformAppMetrics table.
    existingMetrics = DailyPlatformAppMetrics.objects.filter(customer_id=customer,
        platform_app_id=platformApp, date__gte=startDate, date__lt=endDate)

    # Update the dictionary with existing metrics entries, but zero out the metrics that
    # we intend to overwrite.
    for metric in existingMetrics:
      key = metric.date
      metric.dau = 0
      metric.mau = 0
      metric.sessions = 0
      metricsDict[key] = metric

    # Execute the DAU query and update the dictionary.
    cursor = connection.cursor()
    cursor.execute(_SINGLE_PLATFORM_APP_USER_ID_DAU_QUERY,
        [customer.timezone, platformAppId, startTimeStr, endTimeStr])
    for record in cursor.fetchall():
      key = record[0]
      if key in metricsDict:
        metricsDict[key].dau = record[1] if record[1] is not None else 0

    # Execute the MAU query and update the dictionary.
    cursor.execute(_SINGLE_PLATFORM_APP_USER_ID_ACTIVES_QUERY,
        [platformAppId, mauStartTimeStr, endTimeStr])
    for record in cursor.fetchall():
      key = mauPersistDate
      if key in metricsDict:
        metricsDict[key].mau = record[0] if record[0] is not None else 0

    cursor.execute(_SINGLE_PLATFORM_APP_USER_ID_SESSIONS_QUERY, [customer.timezone,
        platformAppId, startTimeStr, endTimeStr, SESSION_START_EVENT_IDS_TUPLE])
    for record in cursor.fetchall():
      key = record[0]
      if key in metricsDict:
        metricsDict[key].sessions = record[1] if record[1] is not None else 0

    cursor.close()

    # Write results to the database
    with transaction.atomic():
      for key in metricsDict:
        metricsDict[key].save()

  except Exception as e:
    # Treat all exceptions as transient errors and retry.
    e.message = 'Daily platform app metrics job for id %s failed with error message: %s' % \
        (platformAppId, e.message)
    raise self.retry(exc=e, countdown=exponential_backoff(self.request.retries))


# Generates product-specific metrics such as daily revenue.
@task(max_retries=_MAX_RETRIES, ignore_result=True, bind=True)
def daily_product_metrics(self, customerId, dateStr):
  try:
    customer = Customer.objects.get(pk=customerId)
    customerTz = timezone(customer.timezone)

    # Calculate the start and end times of the analysis period.
    # The end date is the first date not included in the analysis period.
    # The end time is 12:00AM in the customer's timezone on the end date, expressed in UTC time.
    endTimeUnaware = deserialize_unaware(dateStr) + timedelta(days=1)
    endTime = convert_tz(endTimeUnaware, customerTz, timezone('UTC'))
    endTimeStr = display(endTime)
    endDate = endTimeUnaware.date()
    startTimeUnaware = endTimeUnaware - timedelta(days=1)
    startTime = convert_tz(startTimeUnaware, customerTz, timezone('UTC'))
    startTimeStr = display(startTime)
    startDate = startTimeUnaware.date()

    # Fetch the customer's channelProducts
    channelProducts = ChannelProduct.objects.filter(product_id__customer_id=customer)

    metricsDict = {}
    revShare = {}

    # Prepopulate the dictionary with empty records, and fetch the platform and
    # revenue share for this product.
    for channelProduct in channelProducts:
      # Fetch the platform and revenue share for this product.
      if channelProduct.platform_app_id is not None:
        platform = channelProduct.platform_app_id.platform_type_id.platform_type_str
      elif channelProduct.channel_id.platform_app_id is not None:
        platform = channelProduct.channel_id.platform_app_id.platform_type_id.platform_type_str
      else:
        platform = channelProduct.channel_id.platform_type_id.platform_type_str
      share = _revenue_share(platform)
      revShare[channelProduct.channel_product_id] = share

      for delta in range((endDate - startDate).days):
        date = startDate + timedelta(days=delta)
        key = (channelProduct.channel_product_id, date)
        metricsDict[key] = DailyProductMetrics(customer_id=customer,
            channel_product_id=channelProduct, date=date, revenue=0, recurring_revenue=0,
            developer_revenue_usd_micros=0L, developer_recurring_revenue_usd_micros=0L)

    # Fetch any existing metrics records that would need to be updated instead of inserted.
    # Note that the triple (customer, channelProduct, date) is unique for the
    # DailyProductMetrics table.
    existingMetrics = DailyProductMetrics.objects.filter(customer_id=customer, date__gte=startDate,
        date__lt=endDate)

    # Update the dictionary with existing metrics entries, but zero out the metrics that
    # we intend to overwrite.
    for metric in existingMetrics:
      key = (metric.channel_product_id.channel_product_id, metric.date)
      metric.revenue = 0L
      metric.recurring_revenue = 0L
      metric.developer_revenue_usd_micros = 0L
      metric.developer_recurring_revenue_usd_micros = 0L
      metricsDict[key] = metric

    # Execute the metrics query
    cursor = connection.cursor()
    cursor.execute(_SINGLE_PRODUCT_DAILY_REVENUE_QUERY,
        [customer.timezone, customerId, startTimeStr, endTimeStr])

    # We temporarily assume that each channelProduct is associated with exactly one (possibly null)
    # platformApp. This allows us to overwrite values to be saved to the database.
    #
    # TODO(d-felix): Refactor the database by adding a Channels table with a nullable foreign key
    # that points to PlatformApp. Channel types may remain as informative groupings of channels
    # (e.g. iTunes vs. in-app vs. webstore).
    for record in cursor.fetchall():
      key = (record[0], record[1])
      if key in metricsDict:
        platformRevenue = record[2] if record[2] is not None else 0L
        platformRecurringRevenue = record[3] if record[3] is not None else 0L
        metricsDict[key].revenue = platformRevenue
        metricsDict[key].recurring_revenue = platformRecurringRevenue
        share = revShare.get(record[0], Decimal('1.0'))
        metricsDict[key].developer_revenue_usd_micros = long(platformRevenue * share)
        metricsDict[key].developer_recurring_revenue_usd_micros = \
            long(platformRecurringRevenue * share)

    cursor.close()

    # Write results to the database
    with transaction.atomic():
      for key in metricsDict:
        metricsDict[key].save()

  except Exception as e:
    # Treat all exceptions as transient errors and retry.
    e.message = 'Daily product metrics job for customer %s failed with error message: %s' % \
        (customerId, e.message)
    raise self.retry(exc=e, countdown=exponential_backoff(self.request.retries))


@task(max_retries=_MAX_RETRIES, ignore_result=True, bind=True)
def daily_label_metrics(self, customerId, dateStr, platformAppId):
  try:
    customer = Customer.objects.get(pk=customerId)
    customerTz = timezone(customer.timezone)

    # Calculate the start and end times of the analysis period.
    # The end date is the first date not included in the analysis period.
    # The end time is 12:00AM in the customer's timezone on the end date, expressed in UTC time.
    endTimeUnaware = deserialize_unaware(dateStr) + timedelta(days=1)
    endTime = convert_tz(endTimeUnaware, customerTz, timezone('UTC'))
    endTimeStr = display(endTime)
    endDate = endTimeUnaware.date()
    startTimeUnaware = endTimeUnaware - timedelta(days=1)
    startTime = convert_tz(startTimeUnaware, customerTz, timezone('UTC'))
    startTimeStr = display(startTime)
    startDate = startTimeUnaware.date()

    platformApp = PlatformApp.objects.get(pk=platformAppId)
    customerLabels = CustomerLabel.objects.filter(customer_id__customer_id=customerId)
    idToLabels = {label.customer_label_id: label for label in customerLabels}

    # Build a dictionary of instances to save.
    metricsDict = {}

    # Fetch any existing metrics records that would need to be updated instead of inserted.
    existingMetrics = DailyLabelMetrics.objects.filter(platform_app_id=platformApp,
        date__gte=startDate, date__lt=endDate)

    # Update the dictionary with existing metrics entries, but zero out the metrics that
    # we intend to overwrite.
    for metric in existingMetrics:
      key = (metric.customer_label_id.label, metric.date)
      metric.count = 0
      metricsDict[key] = metric

    # Execute the query and update the dictionary.
    cursor = connection.cursor()
    cursor.execute(_SINGLE_APP_LABEL_QUERY, [customer.timezone, platformAppId,
        startTimeStr, endTimeStr])
    for row in cursor.fetchall():
      customerLabelId, date, count = row[0], row[1], row[2]
      if startDate <= date < endDate:
        labelStr = idToLabels[customerLabelId].label
        key = (labelStr, date)
        if key in metricsDict:
          metricsDict[key].count = count
        else:
          metricsDict[key] = DailyLabelMetrics(platform_app_id=platformApp,
              customer_label_id=idToLabels[customerLabelId], date=date, count=count)

    cursor.close()

    # Write results to the database
    with transaction.atomic():
      for key in metricsDict:
        metricsDict[key].save()

  except Exception as e:
    # Treat all exceptions as transient errors and retry.
    if 'platformApp' in locals():
      e.message = 'Daily label metrics task for platformAppId %s failed with error message: %s' % \
          (platformAppId, e.message)
    raise self.retry(exc=e, countdown=exponential_backoff(self.request.retries))


# Backfills daily metrics for the provided customer for all dates since the provided start date.
@task(max_retries=_MAX_RETRIES, ignore_result=True, bind=True)
def backfill_daily_metrics(self, customerId, startDateStr):
  try:
    customer = Customer.objects.get(customer_id=customerId)
    customerTz = timezone(customer.timezone)

    # Calculate the backfill start and end dates.
    startTimeUnaware = deserialize_unaware(startDateStr)
    startDate = startTimeUnaware.date()
    todayForCustomer = today(timezone(customer.timezone))
    yesterdayForCustomer = todayForCustomer - timedelta(days=1)
    endDate = yesterdayForCustomer

    taskList = []
    for delta in range((endDate - startDate + timedelta(days=1)).days):
      dateToBackfill = startDate + timedelta(days=delta)
      dateToBackfillStr = serialize_unaware(dateToBackfill)
      taskList.append(daily_metrics.s(customerId, dateToBackfillStr))

    backfill = group(taskList)
    backfill.apply_async()

  except Exception as e:
    # Treat all exceptions as transient errors and retry.
    e.message = 'Backfill job for customer %s failed with error message: %s' % \
        (customerId, e.message)
    raise self.retry(exc=e, countdown=exponential_backoff(self.request.retries))
