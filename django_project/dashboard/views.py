import logging
import random
import os
import json
import requests
import time
import operator
from string import split
from dateutil import parser
from pytz import timezone, utc
from dateutil import parser
from bson import json_util
from decimal import Decimal
from itertools import groupby
from collections import defaultdict, Counter
from datetime import date, datetime, time, timedelta
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.core import serializers
from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import redirect
from django.shortcuts import render
from django.db.models import Count
from django.views.decorators.cache import never_cache
from django.templatetags.static import static
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render_to_response
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
#from pure_pagination import Paginator, EmptyPage, PageNotAnInteger

from django.conf import settings
from customers.models import Customer, CustomerExternalLoginInfo
from customers.views import itunes_and_google_account_lists
from appinfo.models import AppInfo, AppScreenshot
from appinfo import fetcher
from dashboard.utils import product_info_for_auth_user, time_info_from_bounds
from dashboard import rankutils
from metrics.googlesalesreports import _parse_decimal
from metrics.models import GoogleReportRecord
from metrics.googlesalesreports import fetch_google_daily_sales_report, fetch_google_report
from metrics.salesreports import fetch_itunes_download_report, fetch_itunes_sales_report
from localization.models import Country

from ad_revenues.ad_revenues import supported_platforms, supported_app_stores, get_service_by_platform
from platform import platforms

from core.cache import cache_key
from core.db.dynamic import connection
from core.timeutils import convert_tz, display, from_timestamp, midnight_timestamp, timestamp, DATE_FMT, utc_epoch, CHART_DATE_FMT
from core.oauth.constants import GSUTIL_CLIENT_ID, GSUTIL_CLIENT_NOTSOSECRET, SERVICE_ACCOUNT
#from core.bigquery import get_client
#from core.bigquery.query_builder import render_query
from customers import bigquery

GOOGLE_CLOUD = CustomerExternalLoginInfo.GOOGLE_CLOUD
ITUNES_CONNECT = CustomerExternalLoginInfo.ITUNES_CONNECT

_PRODUCT_INFO_CACHE_TIMEOUT = 10 * 60
logger = logging.getLogger(__name__)

'''
  the main logged in view
'''


def main_dashboard(request):
    if not request.user.is_authenticated():
        return redirect('/') 
    itunes_accounts, google_play_accounts = itunes_and_google_account_lists(request.user)
    customer = Customer.objects.filter(auth_user=request.user).first()

    ### Evyatar's Addition ###
    u = request.user
    user_platforms = {}
    for c in u.credentials_list.all():
        try:
            fd = c.fid_data
            assets = fd.assets
            status = fd.status
        except:
            assets = 0
            status = "Fetching Data"
        
        co = c.content_object    
        user_platforms[co.platform] = { 'credential':co,
                                        'name': co.platform,
                                        'assets': assets,
                                        'status': status,
                                      }
    '''
    for platform in user_platforms.keys():
        service = get_service_by_platform(platform)
        user_platforms[platform]['assets'] = service.get_assets_count(user_platforms[platform]['credential'])
        user_platforms[platform]['status'] = service.get_status(user_platforms[platform]['credential'])
    '''
    
    ###
    return render(request, 'dashboard/dashboard-main.html',
                {'itunes_accounts': itunes_accounts,
                 'google_play_accounts': google_play_accounts,
                 'platforms': platforms, 
		 ###	Evyatars's Addition ###
                 'supported_platforms' : supported_platforms, 
                 'supported_app_stores': supported_app_stores, 
                 'user_platforms': user_platforms,
		 ###
                 })


#get login customer details
def customer_info(user):
	return Customer.objects.get(auth_user_id=user)


def _time_info(user, start_in_seconds, end_in_seconds):
  return time_info_from_bounds(_user_id(user), start_in_seconds, end_in_seconds)

@login_required	
def apps(request):
    return render(request, 'apps.html')

@login_required	
def app_list(request, platform_type, start_in_seconds,
                                    end_in_seconds):  
    user = request.user
    user_id = request.user.id
    customer = customer_info(user_id)
    timeInfo = _time_info(user, start_in_seconds, end_in_seconds)
    startDate = timeInfo['start_date']
    endDate = timeInfo['end_date']
    start_date = datetime.combine(startDate, time.min)
    end_date = datetime.combine(endDate, time.min)
    
    # get apps associated with the current user.
    appInfos = [ai for ai in AppInfo.objects.filter(customer_id=customer.customer_id, platform='App Store')]
    idToApp = {int(ai.identifier): ai for ai in appInfos}
    apps = (tuple(idToApp))
    
    if platform_type == 'all':
        appinfos = list(AppInfo.objects.filter(customer_id=customer.customer_id).values('app','identifier','app_info_id','icon_url','name','platform',
            'platform_type_id').order_by('name'))
    else:
        appinfos = list(AppInfo.objects.filter(customer_id=customer.customer_id,platform_type_id=platform_type).values('app','identifier','app_info_id',
            'icon_url','name','platform','platform_type_id').order_by('name'))
 
    googleApp =  AppInfo.objects.filter(customer_id=customer.customer_id, platform='Google Play').first()
    itunesApp =  AppInfo.objects.filter(customer_id=customer.customer_id, platform='App Store').first()
    
    if googleApp:
        googleAppdownload = bigquery.get_google_apps_download_data(start_date, end_date, customer.customer_id)
        googleApprevenue = bigquery.get_google_app_revenue_data(start_date, end_date, customer.customer_id)
    if itunesApp:
        itunesAppdownload = bigquery.get_itunes_apps_download_data(start_date, end_date, customer.customer_id)
        itunesApprevenue = bigquery.get_itunes_app_revenue_data(start_date, end_date, customer.customer_id, apps)
            
    
    appData = {}
    for appinfo in appinfos:
        platform_type_id = appinfo['platform_type_id']
        if platform_type_id == 2:
            download = googleAppdownload[appinfo['app']]['download'] if googleAppdownload.has_key(appinfo['app']) else 0
            revenue = googleApprevenue[appinfo['app']]['revenue'] if googleApprevenue.has_key(appinfo['app']) else 0
        else:
            download = itunesAppdownload[int(appinfo['identifier'])]['download'] if itunesAppdownload.has_key(int(appinfo['identifier'])) else 0
            revenue = itunesApprevenue[int(appinfo['identifier'])]['revenue'] if itunesApprevenue.has_key(int(appinfo['identifier'])) else 0
        
        icon = appinfo['icon_url'][:2]
        if icon != 'ht':
            icon_url = '//'+appinfo['icon_url']
        else:
            icon_url =  appinfo['icon_url']
            
        appData[appinfo['app_info_id']] =  {
            'name' : appinfo['name'],
            'id' : appinfo['app_info_id'],
            'icon_url': icon_url,
            'platform': appinfo['platform'],
            'total_download': "{:,}".format(int(download)),
            'total_revenue' : revenue,
        }
    
    #return HttpResponse(json.dumps({'appdetails':appinfos,'platform_id':platform_type}), content_type='application/json')
    return HttpResponse(json.dumps({'platform_id':platform_type,'appdetails':appinfos,'appdatas': appData}), content_type='application/json')



	
# app_id is bundle_id or package depending on platform
# country_ids is 2 char country code
@login_required	
def app_revenue(request, app_id, country_ids='ALL'):
	apps = AppInfo.objects.filter(app_info_id=app_id).first()
	return render(request, 'app_revenue.html',{'app_info':apps})


# app_id is bundle_id or package depending on platform
# country_ids is 2 char country code
@login_required	
def app_download(request, app_id, country_ids='ALL'):
	apps = AppInfo.objects.filter(app_info_id=app_id).first()
	return render(request, 'app_download.html',{'app_info':apps,
				})

	
# app_id is bundle_id or package depending on platform
# country_ids is 2 char country code
@login_required	
def app_download_graph_data_with_range(request, country_ids, app_id, start_in_seconds,
                                    end_in_seconds):
    allcountry_result = get_all_countries()
    apps = AppInfo.objects.filter(app_info_id=app_id).first()
    title = apps.name
    platform_type_id = apps.platform_type_id.platform_type_id
    user = request.user
    if platform_type_id == 2:
        app_str = apps.app
        # return google play app download stats
        result = android_app_download_graph_data(country_ids, app_str, user, start_in_seconds, end_in_seconds)
    else:
        app_str = apps.identifier
        # return itunes app download stats
        result = itunes_app_download_graph_data(country_ids, app_str, user, start_in_seconds, end_in_seconds)
        
    return HttpResponse(json.dumps({'downloadData':result['downloadData'],'chartData':result['chartData'],'current_total':result['current_total'],'previous_total':result['previous_total'],
            'downloadTotalPercentage':result['downloadTotalPercentage'], 'title':title,'all_country_info': allcountry_result}), content_type='application/json')


def itunes_app_download_graph_data(country_ids, app_identifier, user, start_in_seconds, end_in_seconds):
    
    user_id = user.id
    timeInfo = _time_info(user, start_in_seconds, end_in_seconds)
    startDate = timeInfo['start_date']
    endDate = timeInfo['end_date']
    previousStartDate = timeInfo['previous_start_date']
    previousEndDate = timeInfo['previous_end_date']
    
    start_date = datetime.combine(timeInfo['start_date'], time.min)
    end_date = datetime.combine(timeInfo['end_date'], time.min)
    previous_start_date = datetime.combine(timeInfo['previous_start_date'], time.min)
    previous_end_date = datetime.combine(timeInfo['previous_end_date'], time.min)
    
    currentSeries = rankutils.itunes_app_download_data(country_ids, app_identifier, start_date, end_date, user_id)
    previousSeries = rankutils.itunes_app_download_data(country_ids, app_identifier, previous_start_date, previous_end_date, user_id)
    
    current_result = rankutils.itunes_app_download_stats(currentSeries,startDate,endDate,country_ids)
    previous_result = rankutils.itunes_app_download_stats(previousSeries,previousStartDate,previousEndDate,country_ids)
    
    currentTotal = current_result['total']
    previousTotal = previous_result['total']
    differenceTotal = currentTotal-previousTotal
   
    if differenceTotal == 0 or previousTotal == 0:
        downloadTotalPercentage = 'N/A'
    else:
        downloadTotalPercentage = "{:+.0f} %".format(round(Decimal(differenceTotal) / Decimal(previousTotal) * 100, 2))
    
    downloadData = []
    for currentData in current_result['results']:
        country = currentData['country']
        currentCountryTotal = currentData['total']
        
        if currentCountryTotal <= 0:
            totalPercentage = 0
        else:
            totalPercentage = round(Decimal(currentCountryTotal) / Decimal(currentTotal) * 100, 2)
        
        name = currentData['name']
        country_code = currentData['country']
        
        if country not in previous_result['sortedData']:
            previousCountryTotal = 0
        else:
            previousCountryTotal = previous_result['sortedData'][country]
        
        difference = int(currentCountryTotal)-int(previousCountryTotal)
        
        if difference < 0:
            downloadPercentage = "{:+.0f} %".format(round(Decimal(difference) / Decimal(previousCountryTotal) * 100, 2))
            color = 'red'
            previous_total = previousCountryTotal
        elif difference > 0:
            if(previousCountryTotal == 0):
                downloadPercentage = 'N/A'
                color = 'gray'
                previous_total = 'N/A'
            else:
                downloadPercentage = "{:+.0f} %".format(round(Decimal(difference) / Decimal(previousCountryTotal) * 100, 2))
                color = 'grn'
                previous_total = previousCountryTotal
        else:
            if currentCountryTotal > 0 and previousCountryTotal > 0:
                downloadPercentage = '='
            else:
                downloadPercentage = 'N/A'
            color = 'gray'
            previous_total = previousCountryTotal
    
        downloadData.append({'currentTotal':currentCountryTotal, 'country_code':country_code, 'name':name,'previousTotal':previousCountryTotal,'previous_total':previous_total,
            'totalPercentage':totalPercentage,'downloadPercentage':downloadPercentage,'color':color})
    downloadData = sorted(downloadData, key=lambda x: x['currentTotal'], reverse=True)
    
    info = {
        'downloadData':downloadData, 
        'chartData':current_result['chartData'], 
        'current_total':currentTotal,
        'previous_total' : previousTotal,
        'downloadTotalPercentage' : downloadTotalPercentage
    }
    
    return info

"""
 get google play app download stats
"""
# app_id is bundle_id or package depending on platform
# country_ids is 2 char country code    

def android_app_download_graph_data(country_ids, app_identifier, user, start_in_seconds, end_in_seconds):
    user_id = user.id
    timeInfo = _time_info(user, start_in_seconds, end_in_seconds)
    startDate = timeInfo['start_date']
    endDate = timeInfo['end_date']
    previousStartDate = timeInfo['previous_start_date']
    previousEndDate = timeInfo['previous_end_date']
    
    start_date = datetime.combine(timeInfo['start_date'], time.min)
    end_date = datetime.combine(timeInfo['end_date'], time.min)
    previous_start_date = datetime.combine(timeInfo['previous_start_date'], time.min)
    previous_end_date = datetime.combine(timeInfo['previous_end_date'], time.min)
    
    currentSeries = rankutils.android_app_download_data(country_ids, app_identifier, start_date, end_date, user_id)
    previousSeries = rankutils.android_app_download_data(country_ids, app_identifier, previous_start_date, previous_end_date, user_id)
    
    current_result = rankutils.android_app_download_stats(currentSeries,startDate,endDate,country_ids)
    previous_result = rankutils.android_app_download_stats(previousSeries,previousStartDate,previousEndDate,country_ids)
    
    currentTotal = current_result['total']
    previousTotal = previous_result['total']
    differenceTotal = currentTotal-previousTotal
   
    if differenceTotal == 0 or previousTotal == 0:
        downloadTotalPercentage = 'N/A'
    else:
        downloadTotalPercentage = "{:+.0f} %".format(round(Decimal(differenceTotal) / Decimal(previousTotal) * 100, 2))
    
    downloadData = []
    for currentData in current_result['results']:
        country = currentData['country']
        currentCountryTotal = currentData['total']
        
        if currentCountryTotal <= 0:
            totalPercentage = 0
        else:
            totalPercentage = round(Decimal(currentCountryTotal) / Decimal(currentTotal) * 100, 2)
        
        name = currentData['name']
        country_code = currentData['country']
        
        if country not in previous_result['sortedData']:
            previousCountryTotal = 0
        else:
            previousCountryTotal = previous_result['sortedData'][country]
        
        difference = int(currentCountryTotal)-int(previousCountryTotal)
        
        if difference < 0:
            downloadPercentage = "{:+.0f} %".format(round(Decimal(difference) / Decimal(previousCountryTotal) * 100, 2))
            color = 'red'
            previous_total = previousCountryTotal
        elif difference > 0:
            if(previousCountryTotal == 0):
                downloadPercentage = 'N/A'
                color = 'gray'
                previous_total = 'N/A'
            else:
                downloadPercentage = "{:+.0f} %".format(round(Decimal(difference) / Decimal(previousCountryTotal) * 100, 2))
                color = 'grn'
                previous_total = previousCountryTotal
        else:
            if currentCountryTotal > 0 and previousCountryTotal > 0:
                downloadPercentage = '='
            else:
                downloadPercentage = 'N/A'
            color = 'gray'
            previous_total = previousCountryTotal
    
        downloadData.append({'currentTotal':currentCountryTotal, 'country_code':country_code, 'name':name,'previousTotal':previousCountryTotal,'previous_total':previous_total,
            'totalPercentage':totalPercentage,'downloadPercentage':downloadPercentage,'color':color})
    downloadData = sorted(downloadData, key=lambda x: x['currentTotal'], reverse=True)
    
    info = {
        'downloadData':downloadData, 
        'chartData':current_result['chartData'], 
        'current_total':currentTotal,
        'previous_total' : previousTotal,
        'downloadTotalPercentage' : downloadTotalPercentage
    }
    return info
	
@login_required	
def app_details(request, app_id):
	apps = AppInfo.objects.filter(app_info_id=app_id).first()
	appScreenshot = AppScreenshot.objects.filter(app_info_id=apps)
	
	return render(request, 'app_details.html', {'app_info':apps, 'app_screenshots':appScreenshot})

def _user_id(user):
  """
  Returns the auth_user.id of an authenticated user.
  If the user is not authenticated, returns a default value for demonstration purposes.
  """
  return user.id if user.is_authenticated() else settings.DEMO_AUTH_USER_ID



@never_cache
def app_info(request, bundle_id):
  if bundle_id == 'otm-gaia-bundle':
    info = {
        'fields': {
            'name': "Gaia Topo Bundle",
            'icon_url': 'http://is4.mzstatic.com/image/pf/us/r30/Purple5/v4/1d/14/4e/1d144ec7-6645-1fa2-3e76-c8f0e7153501/AppIcon57x57.png',
            'app': 'otm-gaia-bundle',
        }}
    return HttpResponse(json.dumps([info]), content_type='application/json')
  info = fetcher.fetch(bundle_id, "App Store")
  if info:
    info = serializers.serialize("json", [info])
    return HttpResponse(info, content_type='application/json')
  return HttpResponse(json.dumps({'error': "App not found."}), content_type='application/json')


def app_info_android(request, app_id):
  info = fetcher.fetch(app_id, "Google Play")
  if info:
    info = serializers.serialize("json", [info])
    return HttpResponse(info, content_type='application/json')
  return HttpResponse(json.dumps({'error': "App not found."}), content_type='application/json')


def _product_info(user, consult_cache=True):
  userId = _user_id(user)
  cacheKey = cache_key(product_info_for_auth_user, userId)
  if consult_cache:
    info = cache.get(cacheKey)
    if info is not None:
      return info

  info = product_info_for_auth_user(userId)
  cache.set(cacheKey, info, _PRODUCT_INFO_CACHE_TIMEOUT)
  return info


@never_cache
def products(request):
  # todo return enabled info for products, which is saved in save_settings()
  # TODO(d-felix): Return list instead of CSV.
  user = request.user
  consultCache = False
 
  productInfo = _product_info(user, consult_cache=consultCache)
  productCsv = ''
  for key, value in productInfo.iteritems():
    # \todo skipping Gaia Beta Android here, maybe a customer
    # will have a ghost app and we'll fix better
    if key == 57:
      continue
    productCsv += '%s' % value
    productCsv += ','
  if len(productCsv) >= 1 and productCsv[len(productCsv) - 1] == ",":
    productCsv = productCsv[:-1]

  return HttpResponse(json.dumps({"product_string": productCsv}), content_type='application/json')


def graph_app_ranks_data_with_range(request, country_ids, app_id, start_in_seconds, end_in_seconds):
    
    allcountry_result = get_all_countries()
    apps = AppInfo.objects.filter(app_info_id=app_id).first()
    title = apps.name
    platform_type_id = apps.platform_type_id.platform_type_id
    user = request.user
    
    if platform_type_id == 2:
        app_str = apps.app
        result = android_app_revenue_graph_data(country_ids, app_str, user, start_in_seconds, end_in_seconds)
    else:
        app_str = apps.identifier
        result = itunes_app_revenue_graph_data(country_ids, app_str, user, start_in_seconds, end_in_seconds)
	
    return HttpResponse(json.dumps({'revenueData':result['revenueData'],'chartData':result['chartData'],'current_total':result['current_total'],'previous_total':result['previous_total'],
        'revenueTotalPercentage':result['revenueTotalPercentage'], 'title':title,'all_country_info': allcountry_result}), content_type='application/json')
        
def itunes_app_revenue_graph_data(country_ids, app_identifier, user, start_in_seconds, end_in_seconds):
    
    user_id = user.id
    timeInfo = _time_info(user, start_in_seconds, end_in_seconds)
    startDate = timeInfo['start_date']
    endDate = timeInfo['end_date']
    previousStartDate = timeInfo['previous_start_date']
    previousEndDate = timeInfo['previous_end_date']
    
    start_date = datetime.combine(timeInfo['start_date'], time.min)
    end_date = datetime.combine(timeInfo['end_date'], time.min)
    previous_start_date = datetime.combine(timeInfo['previous_start_date'], time.min)
    previous_end_date = datetime.combine(timeInfo['previous_end_date'], time.min)
    
    currentSeries = rankutils.itunes_app_sales_data(country_ids, app_identifier, start_date, end_date, user_id)
    previousSeries = rankutils.itunes_app_sales_data(country_ids, app_identifier, previous_start_date, previous_end_date, user_id)
    
    current_result = rankutils.itunes_app_revenue_stats(currentSeries,startDate,endDate,country_ids)
    previous_result = rankutils.itunes_app_revenue_stats(previousSeries,previousStartDate,previousEndDate,country_ids)
    
    currentTotal = current_result['total']
    previousTotal = previous_result['total']
    differenceTotal = currentTotal-previousTotal
   
    if differenceTotal == 0 or previousTotal == 0:
        revenueTotalPercentage = 'N/A'
    else:
        revenueTotalPercentage = "{:+.0f} %".format(round(Decimal(differenceTotal) / Decimal(previousTotal) * 100, 2))
    
    revenueData = []
    for currentData in current_result['results']:
        country = currentData['country']
        currentCountryTotal = currentData['total']
        
        if currentCountryTotal <= 0:
            totalPercentage = 0
        else:
            totalPercentage = round(Decimal(currentCountryTotal) / Decimal(currentTotal) * 100, 2)
        
        name = currentData['name']
        country_code = currentData['country']
        
        if country not in previous_result['sortedData']:
            previousCountryTotal = 0
        else:
            previousCountryTotal = previous_result['sortedData'][country]
        
        difference = int(currentCountryTotal)-int(previousCountryTotal)
        
        if difference < 0:
            revenuePercentage = "{:+.0f} %".format(round(Decimal(difference) / Decimal(previousCountryTotal) * 100, 2))
            color = 'red'
            previous_total = previousCountryTotal
        elif difference > 0:
            if(previousCountryTotal == 0):
                revenuePercentage = 'N/A'
                color = 'gray'
                previous_total = 'N/A'
            else:
                revenuePercentage = "{:+.0f} %".format(round(Decimal(difference) / Decimal(previousCountryTotal) * 100, 2))
                color = 'grn'
                previous_total = previousCountryTotal
        else:
            if currentCountryTotal > 0 and previousCountryTotal > 0:
                revenuePercentage = '='
            else:
                revenuePercentage = 'N/A'
            color = 'gray'
            previous_total = previousCountryTotal
    
        revenueData.append({'currentTotal':currentCountryTotal, 'country_code':country_code, 'name':name,'previousTotal':previousCountryTotal,'previous_total':previous_total,
            'totalPercentage':totalPercentage,'revenuePercentage':revenuePercentage,'color':color})
    revenueData = sorted(revenueData, key=lambda x: x['currentTotal'], reverse=True)
    
    info = {
        'revenueData':revenueData, 
        'chartData':current_result['chartData'], 
        'current_total':currentTotal,
        'previous_total' : previousTotal,
        'revenueTotalPercentage' : revenueTotalPercentage
    }
    
    return info


def android_app_revenue_graph_data(country_ids, app_str, user, start_in_seconds, end_in_seconds):
    
    user_id = user.id
    timeInfo = _time_info(user, start_in_seconds, end_in_seconds)
    startDate = timeInfo['start_date']
    endDate = timeInfo['end_date']
    previousStartDate = timeInfo['previous_start_date']
    previousEndDate = timeInfo['previous_end_date']
    
    start_date = datetime.combine(timeInfo['start_date'], time.min)
    end_date = datetime.combine(timeInfo['end_date'], time.min)
    previous_start_date = datetime.combine(timeInfo['previous_start_date'], time.min)
    previous_end_date = datetime.combine(timeInfo['previous_end_date'], time.min)
    
    currentSeries = rankutils.google_app_sales_data(country_ids, app_str, start_date, end_date, user_id)
    previousSeries = rankutils.google_app_sales_data(country_ids, app_str, previous_start_date, previous_end_date, user_id)
    
    current_result = rankutils.android_app_revenue_stats(currentSeries,startDate,endDate,country_ids)
    previous_result = rankutils.android_app_revenue_stats(previousSeries,previousStartDate,previousEndDate,country_ids)
    
 
    currentTotal = current_result['total']
    previousTotal = previous_result['total']
    differenceTotal = currentTotal-previousTotal
   
    if differenceTotal == 0 or previousTotal == 0:
        revenueTotalPercentage = 'N/A'
    else:
        revenueTotalPercentage = "{:+.0f} %".format(round(Decimal(differenceTotal) / Decimal(previousTotal) * 100, 2))
    
    revenueData = []
    for currentData in current_result['results']:
        country = currentData['country']
        currentCountryTotal = currentData['total']
        
        if currentCountryTotal <= 0:
            totalPercentage = 0
        else:
            totalPercentage = round(Decimal(currentCountryTotal) / Decimal(currentTotal) * 100, 2)
        
        name = currentData['name']
        country_code = currentData['country']
        
        if country not in previous_result['sortedData']:
            previousCountryTotal = 0
        else:
            previousCountryTotal = previous_result['sortedData'][country]
        
        difference = int(currentCountryTotal)-int(previousCountryTotal)
        
        if difference < 0:
            revenuePercentage = "{:+.0f} %".format(round(Decimal(difference) / Decimal(previousCountryTotal) * 100, 2))
            color = 'red'
            previous_total = previousCountryTotal
        elif difference > 0:
            if(previousCountryTotal == 0):
                revenuePercentage = 'N/A'
                color = 'gray'
                previous_total = 'N/A'
            else:
                revenuePercentage = "{:+.0f} %".format(round(Decimal(difference) / Decimal(previousCountryTotal) * 100, 2))
                color = 'grn'
                previous_total = previousCountryTotal
        else:
            if currentCountryTotal > 0 and previousCountryTotal > 0:
                revenuePercentage = '='
            else:
                revenuePercentage = 'N/A'
            color = 'gray'
            previous_total = previousCountryTotal
    
        revenueData.append({'currentTotal':currentCountryTotal, 'country_code':country_code, 'name':name,'previousTotal':previousCountryTotal,'previous_total':previous_total,
            'totalPercentage':totalPercentage,'revenuePercentage':revenuePercentage,'color':color})
    revenueData = sorted(revenueData, key=lambda x: x['currentTotal'], reverse=True)
    
    info = {
        'revenueData':revenueData, 
        'chartData':current_result['chartData'], 
        'current_total':currentTotal,
        'previous_total' : previousTotal,
        'revenueTotalPercentage' : revenueTotalPercentage
    }
    
    return info


def get_country_list(request):
  countries = rankutils.all_countries()
  return HttpResponse(json.dumps(countries), content_type='application/json')

def get_all_countries():
    all_countries = rankutils.all_countries()
    allcountry_result = {} 
    for countryData in all_countries:
        country_id = countryData['id']
        country_name = countryData['name']
        allcountry_result[country_id] = {}
        allcountry_result[country_id]['id'] = country_id
        allcountry_result[country_id]['name'] = country_name
        allcountry_result[country_id]['top'] = countryData['top']
    
    return allcountry_result
