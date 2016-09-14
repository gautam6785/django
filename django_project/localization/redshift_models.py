from core.models import TimestampedModel
from django.db import models


class Country(TimestampedModel):
  id = models.IntegerField(primary_key=True)
  name = models.CharField(max_length=1024, unique=True)
  alpha2 = models.CharField(max_length=8, unique=True)
  alpha3 = models.CharField(max_length=12, unique=True)
  numeric = models.CharField(max_length=12, unique=True)

  class Meta:
    db_table = 'countries'
    verbose_name = 'country'
    verbose_name_plural = 'countries'
