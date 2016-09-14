from django.db import models
from django.contrib.auth.models import User
from core.oauth2client.django_orm import CredentialsField
from appinfo.models import AppInfo
###
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType


class credentials(models.Model):
        user = models.ForeignKey(
                User,
                on_delete=models.CASCADE,
                #primary_key=True,
                related_name='credentials_list',
        )
        
        content_type = models.ForeignKey(
            ContentType,
            on_delete=models.CASCADE,
        )
        object_id = models.PositiveIntegerField()
        content_object = GenericForeignKey('content_type', 'object_id')
            

class chartboost_credentials(models.Model):
	
	name = models.CharField(max_length=100, null=True)
	user_id = models.CharField(max_length=50, null=True)
	signature = models.CharField(max_length=256, null=True)	
        platform = 'chartboost'
        
        
class vungle_credentials(models.Model):
        
        name = models.CharField(max_length=100, null=True)
        api_key = models.CharField(max_length=50, null=True) 
        platform = 'vungle'
        
        
class adcolony_credentials(models.Model):
        
        name = models.CharField(max_length=100, null=True)
        api_key = models.CharField(max_length=50, null=True) 
        platform = 'adcolony'
        
class inmobi_credentials(models.Model):
        
        email = models.CharField(max_length=200, null=True)
        password = models.CharField(max_length=256, null=True)
        api_key = models.CharField(max_length=50, null=True) 
        account_id = models.CharField(max_length=100, null=True)
        session_id = models.CharField(max_length=100, null=True)
        platform = 'inmobi'
        
class tapjoy_credentials(models.Model):
        
        email = models.CharField(max_length=200, null=True)
        api_key = models.CharField(max_length=50, null=True) 
        platform = 'tapjoy'
        
class admob_credentials(models.Model):
	
	credential = CredentialsField() or None
	platform = 'admob'
	
class adx_credentials(models.Model):
        
        credential = CredentialsField() or None
        platform = 'adx'
        
class facebook_credentials(models.Model):
        
	token = models.CharField(max_length=256, null=True)        
        platform = 'facebook'

class foreign_ids(models.Model):
	
        app_info = models.ForeignKey(
                AppInfo,
                on_delete=models.CASCADE,
                related_name='foreign_ids',
        )
        platform_info =  models.ForeignKey(
                credentials,
                on_delete=models.CASCADE,
                related_name='foreign_ids',
        )
        platform = models.CharField(max_length=100, null=True)
	foreign_id    = models.CharField(max_length=100, null=True)


class fid_data(models.Model):
    cred = models.OneToOneField(
        credentials, 
        on_delete=models.CASCADE,
        null=True,
        related_name='fid_data',
    )
    assets = models.IntegerField(default=0)
    status = models.CharField(default='', max_length=100)


class adtech_credentials(models.Model):
    
        username = models.CharField(max_length=100, null=True)
        password = models.CharField(max_length=256, null=True)
	token    = models.CharField(max_length=256, null=True)

        platform = 'adtech'