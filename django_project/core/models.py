from django.db import models

class TimestampedModel(models.Model):
  """
  An abstract base class model that provides self-updating ``creationTime`` and ``lastModified``
  fields.
  """
  creation_time = models.DateTimeField(auto_now_add=True)
  last_modified = models.DateTimeField(auto_now=True)

  class Meta:
    abstract = True
