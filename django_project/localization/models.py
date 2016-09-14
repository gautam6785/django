from core.models import TimestampedModel
from django.db import models


class Country(TimestampedModel):
  id = models.AutoField(primary_key=True)
  name = models.CharField(unique=True, max_length=255, db_index=True)
  display_name = models.CharField(max_length=256)
  alpha2 = models.CharField(max_length=2, unique=True, db_index=True)
  alpha3 = models.CharField(max_length=3, unique=True, db_index=True)
  numeric = models.CharField(max_length=3, unique=True, db_index=True)

  class Meta:
    db_table = 'countries'
    verbose_name = 'country'
    verbose_name_plural = 'countries'
