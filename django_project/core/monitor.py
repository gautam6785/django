import logging

from boto.ec2.cloudwatch import connect_to_region
from core.timeutils import from_timestamp, utc_epoch
from django.conf import settings
from pytz import utc

logger = logging.getLogger(__name__)

# Note that this class is not threadsafe.
class CloudWatchCounter():
  def __init__(self, name, dispatch_threshold=60):
    self.connection = None
    self.count = 0
    self.dispatchThreshold = dispatch_threshold
    self.lastDispatchEpoch = utc_epoch()
    self.name = name

  def connect(self):
    self.connection = connect_to_region(settings.CLOUDWATCH_REGION) \
        if settings.ENABLE_CLOUDWATCH else None

  def is_ready(self):
    return (utc_epoch() - self.lastDispatchEpoch) >= self.dispatchThreshold

  def increment(self):
    self.count += 1

  def dispatch_results(self):
    dispatchTimestamp = utc_epoch()
    dispatchDatetime = from_timestamp(dispatchTimestamp, utc)
    if settings.ENABLE_CLOUDWATCH:
      self.connection.put_metric_data(namespace=settings.CLOUDWATCH_NAMESPACE, name=self.name,
          timestamp=dispatchDatetime, unit='Count',
          statistics={'maximum': 1, 'minimum': 1, 'samplecount': self.count, 'sum': self.count})
    else:
      logger.info("Current %s count is: %s" % (self.name, self.count))
    self.lastDispatchEpoch = dispatchTimestamp
    self.count = 0
