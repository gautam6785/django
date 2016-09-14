from generic import generic_service
import requests
import json
import traceback,sys
import time,datetime
from ad_revenues.ad_revenues import get_user_creds, round_timestamp, date2timestamp, get_days_array, countryCode2Name
from ad_revenues.models import chartboost_credentials, credentials
from django.http import HttpResponse, Http404, JsonResponse


chartboost_urls = {
    'all_apps': 'https://api.chartboost.com/apps/',
    'appcountry': 'https://analytics.chartboost.com/v3/metrics/appcountry',
    'app': 'https://analytics.chartboost.com/v3/metrics/app',
    'validate': 'https://api.chartboost.com/account',
    'app_info': 'https://api.chartboost.com/apps/',
}

class chartboost_service(generic_service):

    def signup(self,request):
        
        r = request.POST
        try:
                id = r.get('user_id')
                signature=r.get('user_sig')
                name=r.get('display_name')
                valid = self.chartboost_validate(id, signature)
                if valid:
                        cc = chartboost_credentials(
                          user_id = id,
                          signature= signature,
                          name = name,
                        )
                        cc.save()
                        gc=credentials(user=request.user,content_object=cc)
                        gc.save()
                        return HttpResponse("1")
        except:
                #traceback.print_exc(file=sys.stdout)
                return HttpResponse("0")
        return HttpResponse("0")
    

    def chartboost_validate(self, id, sig):
        data = {
          'user_id':id,
          'user_signature':sig,
        }
        res = requests.get(chartboost_urls['validate'], params=data)
        if res.status_code == 200:
                return True
        else:
                return False
        
    def validate(self, credentials):
        uid = credentials.user_id
        sig = credentials.signature
        return self.chartboost_validate(uid, sig)
    
    
    def get_all_apps(self, credentials):
        try:
            user_id = credentials.user_id
            user_signature = credentials.signature
            
            params = {'user_id':user_id, 'user_signature': user_signature }
            response = requests.get(chartboost_urls['all_apps'], params=params)
            return json.loads(response.text)
        except:
            #traceback.print_exc(file=sys.stdout)
            return {}
    
    def get_all_apps_names(self, credentials):
        try:
            apps = self.get_all_apps(credentials)
            #names = [ "%s - %s" % (a['platform'],a['name']) for a in apps.values() ]
            names = []
            for a in apps.values():
                platform = 'Google Play' if a['platform'] == 'android' else 'App Store'
                names.append( {'name':a['name'], 'platform':a['platform'], 'id':a['id']})
            names.sort(key=lambda x: x['name'])
            return names
        except:
            #traceback.print_exc(file=sys.stdout)
            return []
    
    
    def produce_chart_json(self, user, app_id, breakdownBy, countries, since=0, until=0):
        token = self.get_user_signature(user)
        id = self.get_user_id(user)
        since = round_timestamp(since)
        until = round_timestamp(until)
        
        curr_total_by_country_by_month = self.app_revenues_by_country(id, token, app_id, since, until, 'monthly')
        curr_total_by_country = self.total_sum_dates(curr_total_by_country_by_month)
        curr_total_data = curr_total_by_country['total'] 
        curr_data = self.app_revenues_by_country(id, token, app_id, since, until, 'daily')
        
        if breakdownBy == 'country':
            chartData = self.chartboost2json(curr_data,countries,since,until)
        elif breakdownBy == 'platform':
            chartData = self.chartboost2json_generic(curr_data,countries,since,until)
        else:
            chartData = {}
            
        cb_data = {}
        cb_data["chartData"] = chartData
        return cb_data["chartData"]
    
    
    

    def chartboost2json(self, curr_data,countries,since,until):
            _json = {}
            days_array = get_days_array(since,until)
            for item in curr_data:
                    countryCode = str(item['countryCode'])
                    if countries and not countryCode in countries:
                        continue
                    countryName = countryCode2Name(countryCode) 
                    if not _json.has_key(countryName):
                            _json[countryName] = {}
                            _json[countryName]['key'] = countryName
                            _json[countryName]['values'] = [ [i,0] for i in days_array ]
                            _json[countryName]['total'] = 0
                    cb_time = str(item['dt'])
                    chart_time = self.date2millis(cb_time)
                    revenue = float(item['moneyEarned'])
                    index = days_array.index(chart_time)
                    _json[countryName]['values'][index][1] = revenue
                    _json[countryName]['total'] += revenue
            return _json

    def chartboost2json_generic(self, curr_data,countries,since,until):
            days_array = get_days_array(since,until)
            _json = {'key':'chartboost', 'values':[ [i,0] for i in days_array ], 'total':0 }
            for item in curr_data:
                countryCode = str(item['countryCode'])
                if countries and not countryCode in countries:
                    continue                    
                
                cb_time = str(item['dt'])
                chart_time = self.date2millis(cb_time)
                revenue = float(item['moneyEarned'])
                index = days_array.index(chart_time)
                _json['values'][index][1] += revenue
                _json['total'] += revenue
            return _json

    def date2millis(self,cb_time):
            tt = datetime.datetime.strptime(cb_time, "%Y-%m-%d")
            t = time.mktime(tt.timetuple())
            return int(t*1000)

  

    def app_revenues_by_country(self, user_id ,user_signature, appId, since, until, aggregate):
        since = adjustDate(since)
        data = {
            'userId':user_id,
            'userSignature': user_signature,
            'appIds': appId, 
            'dateMax': date2timestamp(until),
            'dateMin': date2timestamp(since),
            'aggregate': aggregate,
            'groupBy': 'app',
            'role': 'publisher',
            }
        response = requests.get(chartboost_urls['appcountry'], params=data)
        _json = json.loads(response.text)
        return _json
    
    
    def get_user_signature(self, user):
        c = get_user_creds(user,'chartboost')
        return str(c.content_object.signature)

    def get_user_id(self, user):
            c = get_user_creds(user,'chartboost')
            return str(c.content_object.user_id)

    def app_data(self, id, token, app_id):
            data = {
                    'user_signature':token,
                    'user_id': id,
                    'app_id' : app_id,
            }
            url = chartboost_urls['app_info'] + app_id
            res = requests.get(url, params=data)
            return json.loads(res.text)


    def total_sum_dates(self, data):
            ctar = {'total':0, 'byCountry':{}}
            
            for item in data:
                    countryCode = str(item['countryCode'])
                    if not ctar['byCountry'].has_key(countryCode):
                            ctar['byCountry'][countryCode] = 0
                    else:
                            ctar['byCountry'][countryCode] += float(item['moneyEarned'])
                    ctar['total'] += float(item['moneyEarned'])
            return ctar    
    
    def get_total_ad_revenues_by_country(self, user, app_id, countries=[], since=0, until=0):
        token = self.get_user_signature(user)
        id = self.get_user_id(user)
        since = round_timestamp(since)
        until = round_timestamp(until)
        
        curr_total_by_country_by_month = self.app_revenues_by_country(id, token, app_id, since, until, 'monthly')
        curr_total_by_country = self.total_sum_dates(curr_total_by_country_by_month)    
        
        return curr_total_by_country['byCountry']
        
        
        
        
def adjustDate(since):
    # adjustDate - check if since is more then 40 days ago
    #if it is , return date of 40 days ago
    now = time.time()
    dlt = datetime.timedelta(seconds=now-since)
    days = dlt.days
    if days >= 40:
        _40days = datetime.timedelta(days=40)
        since = now - _40days.total_seconds()
    print "adjust: ", since
    return since
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        