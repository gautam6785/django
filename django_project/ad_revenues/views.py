import logging
import random
import os
import json
import requests
import ad_revenues
import sys, traceback
from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.http import HttpResponse, Http404, JsonResponse
from django.views.decorators.http import require_http_methods
from django.shortcuts import redirect, render, render_to_response
from appinfo.models import AppInfo

from models import credentials, foreign_ids, facebook_credentials, chartboost_credentials, admob_credentials, adx_credentials
from ad_revenues import supported_platforms
from ad_revenues import get_user_creds, __get_user_apps, get_service_by_platform, is_duplicate_platform


@login_required
def add_platform(request):
	return render(request, 'ad_revenues/add_platform.html',
                {'supported_platforms': supported_platforms, 
		})

@login_required
def platform_signup(request, platform):
    try:
        if is_duplicate_platform(request.user, platform):
            err = {'alert': "You already signed %s as one of your platforms" % platform }
            return HttpResponse(json.dumps(err))
        else:
            service = get_service_by_platform(platform)
            return service.signup(request)
    except:
        traceback.print_exc(file=sys.stdout)
        return HttpResponse(json.dumps({'alert':"Unexpected error occured while signing up"}))
    
# Admob:
##########

@login_required
def auth2callback(request):
        try:
            service = get_service_by_platform('admob')
        
            if request.GET.__contains__('error'):
                return redirect('/dashboard/?success=-1')
            code = request.GET.get('code')
            creds = service.get_credentials(code)
            c = admob_credentials(credential=creds)
            c.save()
            gcred = credentials(user=request.user,content_object=c)
            gcred.save()
            return redirect("/dashboard/?success=1")
        except:
            traceback.print_exc(file=sys.stdout)
            return redirect('/dashboard/?success=0')

# Adx: 
#########
@login_required
def adx_callback(request):
        try:
            service = get_service_by_platform('adx')
        
            if request.GET.__contains__('error'):
                return redirect('/dashboard/?success=-1')
            code = request.GET.get('code')
            creds = service.get_credentials(code)
            c = adx_credentials(credential=creds)
            c.save()
            gcred = credentials(user=request.user,content_object=c)
            gcred.save()
            return redirect("/dashboard/?success=1")
        except:
            traceback.print_exc(file=sys.stdout)
            return redirect('/dashboard/?success=0')

# facebook:
#############

@login_required    
@require_http_methods(["GET"])    
def facebook_callback(request):
    
    service = get_service_by_platform('facebook')
    
    if request.GET.__contains__('code'):
        code = request.GET.get('code')
    else:
        return redirect('/dashboard/?success=0')
        #return HttpResponse('Failed to aquire code')
    
    res = service.code_to_token(code)
      
    if res.text:
        parsed_text = service.parse_facebook_callback(res.text)
        creds = facebook_credentials(token=parsed_text['access_token'])
	creds.save()
        gcreds= credentials(user=request.user, content_object=creds)
	gcreds.save()
        return redirect("/dashboard/?success=1")
    else:
    	return redirect("/dashboard/?success=0")

##########################################################3
@login_required
def app_connections(request, app_id):
    app = AppInfo.objects.filter(app_info_id=app_id).first()
    
    app_fids = app.foreign_ids.all()
    fids_names = [ i.platform for i in app_fids]
    platforms = supported_platforms.keys()
    for fn in fids_names:
        if fn in platforms:
            platforms.remove(fn)
            
    #print "platforms: ", platforms
    
    return render(request, 'ad_revenues/app_connections.html',
                  {
                        'app_info': app,
                        'platforms': platforms,
                  })

@login_required
def app_revenues(request, app_id, country='ALL'):
	app = AppInfo.objects.filter(app_info_id=app_id).first()
	
        foreign_ids = app.foreign_ids.all()
            
        return render(request, 'ad_revenues/app_revenues.html',
                {
                    'app_info':app,
                    'foreign_ids_len': len(foreign_ids),
                })

from ad_revenues import get_chartData, unify_charts,get_top5_countries, get_all_countries, validate_chartGraph

def app_ad_revenues(request, app_id, countries, breakdownBy, since, until):

	app = AppInfo.objects.filter(app_info_id=app_id).first()
	foreign_ids = app.foreign_ids.all()
	
	if breakdownBy == 'country':
            charts = [get_chartData(request.user, fid.platform, fid.foreign_id, breakdownBy, parse_countries(countries), since, until) 
                        for fid in foreign_ids ]
            unified_chart = unify_charts(charts)
            top5 = get_top5_countries(unified_chart)
            chartData = [unified_chart[t] for t in top5]
            retVal = {"chartData":chartData, "othersData":unified_chart.values(), 'all_country_info': get_all_countries()}
        elif breakdownBy == 'platform':
            charts = [get_chartData(request.user, fid.platform, fid.foreign_id, breakdownBy, parse_countries(countries), since, until) 
                        for fid in foreign_ids ]
            charts.reverse()
            othersData = charts
            retVal = {"chartData": charts, "othersData":othersData, 'all_country_info': get_all_countries()}
        else:
            retVal = {"chartData": []}

        ''' 
        #Unit Tests:
        validate_chartGraph(retVal)
        
        with open("/tmp/output.log", "w") as f:
            json.dump(retVal["chartData"], f, sort_keys = True, indent = 4)
        '''
        return HttpResponse(json.dumps(retVal))
            

def parse_countries(countries):
  if countries == "ALL":
    return []
  return countries.split(",")

#############
# adtech
#############
#from .ad_revenues import adtec_validate, adtech_pull_reports
#from .models import adtech_credentials
#@login_required
#@require_http_methods(["POST"])
#def adtech_signup(request):
        #r = request.POST
        #try:
                #username = r.get('login_name')
                #password =r.get('login_password')
                #token = adtec_validate(username, password)
                #if token:
                        #ac = adtech_credentials(user=request.user, 
                          #password = password,
                          #username = username,
			  #token    = token,
                        #)
                        #ac.save()
                        #gc = credentials(user=request.user, content_object=ac)
                        #gc.save()
                        #return HttpResponse("1")
        #except:
		#traceback.print_exc(file=sys.stdout)
        #return HttpResponse("0")

#@login_required
#def adtech_pull_reports(request):
	#reports = adtech_pull_reports(requests.user)
	#return HttpResponse(reports)

#########################################################

@login_required
def remove_platform(request, platform):
    try:
        user = User.objects.filter(id=request.user.id).first()
        
        creds = user.credentials_list.all()
        for cred in creds:
            if cred.content_object.platform == platform:
                cred.delete()
    except:
        traceback.print_exc(file=sys.stdout)
        pass
    return redirect("/dashboard")


@login_required
@require_http_methods(["POST"])
def connect_app(request, platform, fid):
    try:
        # get the user's app id to connect with:
        local_app_id = request.POST.get('app_id')
        
        # get the respective application model
        app_info = AppInfo.objects.filter(app_info_id=local_app_id).first()
        
        # input checking 
        if app_info is None:
            messages.add_message(request, messages.INFO, "No Such Application")
            return redirect('/ad-revenues/platform_connections/'+platform)
      
        # get the user's credentials for the platform
        c = get_user_creds(request.user, platform)
        
        # input check
        if c is None:
            messages.add_message(request, messages.INFO, "You must add %s platform first" % platform )
            return redirect('/ad-revenues/platform_connections/'+platform)

        # extract the foreign_id model according to forign_id got from url
        foreign_id = c.foreign_ids.filter(foreign_id=fid).first()
        
        # if exists     - must unlink it first
        # else          - create forign_id model
	if foreign_id:
		foreign_id.app_info= app_info
	else:
		foreign_id = foreign_ids(app_info=app_info, platform_info=c, platform=platform, foreign_id=fid)
	foreign_id.save()
	
	return redirect('/ad-revenues/platform_connections/'+platform)
    except :
	traceback.print_exc(file=sys.stdout)
	return redirect('/ad-revenues/platform_connections/'+platform)


@login_required
@require_http_methods(["POST"])
def connect_app2platform(request, app_id):
    try:
        # get the user's app id to connect with:
        fid = request.POST.get('foreign_id')
        platform = request.POST.get('platform')
        #print (fid, platform)
        # get the respective application model
        app_info = AppInfo.objects.filter(app_info_id=app_id).first()
        
        # input checking 
        if app_info is None:
            messages.add_message(request, messages.INFO, "No Such Application")
            return redirect('/ad-revenues/app_connections/'+app_id)
      
        # get the user's credentials for the platform
        cred = get_user_creds(request.user, platform)
        
        # input check
        if cred is None:
            messages.add_message(request, messages.ERROR, "User Has No Ad Account Connection For: %s" % platform, extra_tags='ADD_ACCOUNT' )
            return redirect('/ad-revenues/app_connections/'+app_id)

        # extract the foreign_id model according to forign_id got from url
        foreign_id = cred.foreign_ids.filter(foreign_id=fid).first()
        
        # if exists     - must unlink it first
        # else          - create forign_id model
        if foreign_id:
            messages.add_message(request, messages.INFO, "Link is Already Exists")
            return redirect('/ad-revenues/app_connections/'+app_id)
        else:
            foreign_id = foreign_ids(app_info=app_info, platform_info=cred, platform=platform, foreign_id=fid)
        foreign_id.save()
        
        return redirect('/ad-revenues/app_connections/'+app_id)
    except :
        traceback.print_exc(file=sys.stdout)
        return redirect('/ad-revenues/app_connections/'+app_id)




@login_required
def delete_connection(request, platform, fid):
    
    # get credential fo platform:
    c = get_user_creds(request.user, platform)
    # input check
    if c is None:
        messages.add_message(request, messages.INFO, "No Such platform: %s" % platform )
        return redirect('/ad-revenues/platform_connections/'+platform)
    
    # extract foreign_id object:
    foreign_id = c.foreign_ids.filter(foreign_id=fid).first()
    
    # if exists: delete it
    if foreign_id is not None:
        foreign_id.delete()
    
    return redirect('/ad-revenues/platform_connections/'+platform)


@login_required
def platform_connections(request, platform):
    user = request.user
    c = get_user_creds(user,platform)
    p = c.content_object
    
    service = ad_revenues.get_service_by_platform(platform)
    platform_apps = service.get_all_apps_names(p)
    ## platform app format: 
    ## [ {name, platform, foreign_id} ] 
    linked_apps = c.foreign_ids.all()
    
    for pa in platform_apps:
        pa['linked'] = None
        for lan in linked_apps:
            if pa['id'] == lan.foreign_id:
                pa['linked'] = lan.app_info.platform +" - "+ lan.app_info.name 
    
    Apps = __get_user_apps(user)
    Apps.sort(key=lambda x:x.name)
    Apps.sort(key=lambda x:x.platform)
    
    if p is not None:
        return render(request,
                      "ad_revenues/platform_links.html",
                      {'platform': p, 'platform_apps':platform_apps, 'Apps':Apps},
                      )
    raise Http404("No signed platform named %s" % platform)


from ad_revenues import round_timestamp, countryCode2Name
from ad_revenues import get_total_ad_revenues_by_country, get_google_downloads_and_revenues, get_itunes_downloads_and_revenues

def get_arpu_data(user, app_info_id, since, until):

    app = AppInfo.objects.filter(app_info_id=app_info_id).first()
    #print "app_str: ", app.app
    store = app.platform
    
    app_data = {}
    if store == "App Store":
        app_data = get_itunes_downloads_and_revenues(user, app_info_id, since, until)
    elif store == "Google Play":
        app_data = get_google_downloads_and_revenues(user, app_info_id, since, until)

    ad_revenues_data = get_total_ad_revenues_by_country(user, app_info_id, since, until)
    
    _json = {}
    max_arpu = 0
    for country_data in app_data:
        country = countryCode2Name(country_data['country'])
        if not country in _json:
            _json[country] = {}
        _json[country]['country'] = country
        _json[country]['downloads'] = country_data['downloads']
        _json[country]['revenues'] = country_data['revenues'] or 0
        _json[country]['ad_revenues'] = 0 if not country in ad_revenues_data else ad_revenues_data[country]
        _json[country]['arpu'] = (_json[country]['revenues'] + _json[country]['ad_revenues'])/country_data['downloads']
        max_arpu = max(max_arpu, _json[country]['arpu'])
    return _json.values(), max_arpu

from time import time,mktime
from datetime import datetime, timedelta

@login_required
def get_arpu_in_range(request, app_info_id, since, until):
    try:
        
        user = request.user
        arpu_data, max_arpu = get_arpu_data(user, app_info_id, since, until)
        
        arpu_data.sort(key=lambda x:x['arpu'], reverse=True)
        return HttpResponse(json.dumps({"arpu_data":arpu_data, "max_arpu":max_arpu}))
    except: 
        traceback.print_exc(file=sys.stdout)
        return HttpResponse(json.dumps({}))


def app_arpu(request, app_info_id):
    
    app = AppInfo.objects.filter(app_info_id= app_info_id).first()
    
    return render(request, "ad_revenues/app_arpu.html",{'app_info':app })


