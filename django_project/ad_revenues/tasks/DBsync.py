from celery import chain, chord, group, task
from django.contrib.auth.models import User
from celery.utils.log import get_task_logger
from ad_revenues.ad_revenues import get_service_by_platform
from ad_revenues.models import fid_data

logger = get_task_logger(__name__)

_MAX_RETRIES = 5
_10_MINUTES_SECS = 600
# this task will define and run asyncroneus sub task to sync the DB
@task(max_retries=_MAX_RETRIES, bind=True)
def db_sync(self, *args, **kwargs):
    try:
        users = User.objects.all()
        users_ids = [ u.id for u in users ]
        
        jobs  = group( fid_data_sync.s(uid) for uid in users_ids )
        jobs.apply_async()
        
    except Exception as e:
        logger.info ("Failed To complete the task")
        #raise self.retry(exc=e, countdown=_10_MINUTES_SECS)
        
        
@task(bind=True)
def fid_data_sync(self, uid):
    user = User.objects.filter(id=uid).first()
    
    if not user:
        logger.info("No Such User [id: {0}]".format(uid))
        return
    
    creds = user.credentials_list.all()
    
    #for each credential
    for c in creds:
        #get actual credential
        f = c.content_object
        platform = f.platform
        
        #log:
        logger.info("synching user {0}'s {1} platform.".format(user.username, platform))
        
        #get service according to credential platfrm
        service = get_service_by_platform(platform)
        #get fid_data from credentials object
        try:
            f_data = c.fid_data
        except:
            f_data = None
        
        #fetch assets and status according to service
        assets_count = service.get_assets_count(f)
        status = service.get_status(f)
        
        
        if f_data is None:
            logger.info("Got Null fid_data. Generating one now")
            f_data = fid_data(cred=c, assets=assets_count, status=status)
        else:    
            f_data.assets = assets_count
            f_data.status = status
        f_data.save()
        
    logger.info("successfully updated data for user {0}'s platforms.".format(user.username))
        
        
        
        
        
        
        
        
        