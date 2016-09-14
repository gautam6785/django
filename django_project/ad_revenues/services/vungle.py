from generic import generic_service
import requests
import json
import traceback,sys
import time,datetime
from ad_revenues.ad_revenues import get_user_creds, round_timestamp, date2timestamp, get_days_array, countryCode2Name
from ad_revenues.models import vungle_credentials, credentials
from django.http import HttpResponse, Http404, JsonResponse

vungle_urls = {
    'validate'          : 'https://ssl.vungle.com/api/applications',
    'applications'      : 'https://ssl.vungle.com/api/applications',
    }

class vungle_service(generic_service):
    
    def get_api_key(self, user):
        c = get_user_creds(user,'vungle')
        return str(c.content_object.api_key)
    
    def signup(self,request):
        
        r = request.POST
        try:
                name=r.get('display_name')
                api_key = r.get('api_key')
                valid = self.vungle_validate(api_key)
                if valid:
                        vc = vungle_credentials(
                          name = name,
                          api_key = api_key,
                        )
                        vc.save()
                        gc=credentials(user=request.user,content_object=vc)
                        gc.save()
                        res = {"message": "Account added successfully", "color": "green"}
                        return HttpResponse(json.dumps(res))
        except:
                #traceback.print_exc(file=sys.stdout)
                res = {"message": "Error occured while adding account", "color": "red"}
                return HttpResponse(json.dumps(res))
            
        res = {"message": "Invalid Account Credentials", "color": "red"}
        return HttpResponse(json.dumps(res))
    
    
    def get_all_apps_names(self,credentials):
        try:
            api_key = credentials.api_key
            url = vungle_urls['applications']
            params = {"key": api_key}
            res = requests.get(url, params=params)
            response = json.loads(res.text)
            
            apps = []
            for app in response:
                a = {'name': app['name'], 'id':app['id'], 'platform':app['platform']}
                apps.append(a)
                
            return apps
        except:
            #traceback.print_exc(file=sys.stdout)
            return []
    
    def produce_chart_json(self, user, app_id, breakdown, countries, since=0, until=0):
        
        api_key = self.get_api_key(user)
        
        since = round_timestamp(since)
        until = round_timestamp(until)
        
        curr_data_by_country = self.get_app_revenues(api_key , app_id, since, until)
        
        #curr_data_total = curr_data_by_country['total']
        
        if breakdown == 'country':
            chartData = self.vungle2json(curr_data_by_country,countries,since,until)
        elif breakdown == 'platform':
            chartData = self.vungle2json_generic(curr_data_by_country,countries,since,until)
        else:
            chartData = {}
            
        cb_data = {}
        cb_data["chartData"] = chartData
        return cb_data["chartData"]
    
    def get_app_revenues(self, api_key , appId, since, until):
        
        data = {
            'key': api_key,
            'start': date2timestamp(since),
            'end': date2timestamp(until),
            'geo': 'all',
            }
            
        url = "{0}/{1}".format(vungle_urls['applications'],appId)
        response = requests.get(url, params=data)
        _json = json.loads(response.text)
        return _json
    
    
    def get_total_ad_revenues_by_country(self, user, app_id, countries=[], since=0, until=0):
        api_key = self.get_api_key(user)
        
        since = round_timestamp(since)
        until = round_timestamp(until)
        
        curr_data_by_country = self.get_app_revenues(api_key , app_id, since, until)
        _json = {}
        for date_data in curr_data_by_country:
            
            countries_data = date_data['geo_eCPMs']
            v_time = str(date_data['date'])
            chart_time = self.date2millis(v_time)
            
            for country_data in countries_data:
                countryCode = str(item['country'])
                
                if countries and not countryCode in countries:
                    continue
                
                countryName = countryCode2Name(countryCode)
                revenue = float(country_data['revenue'])
                if not _json.has_key(countryName):
                    _json[countryName] =  revenue
                else:
                    _json[countryName] += revenue
        return _json
    
    def vungle_validate(self,api_key):
        ## will try to fetch the applications list of the user ##
        url = vungle_urls['validate']
        params = {"key": api_key}
        res = requests.get(url, params=params)
        #print res.text
        response = json.loads(res.text)
        if 'code' in response:
            ## got an error message ##
            return False
        return True
    
    def validate(self, credentials):
        api_key = credentials.api_key
        return self.vungle_validate(api_key)
    
    def vungle2json(self, curr_data, countries, since, until):
            days_array = get_days_array(since,until)
            
            _json = {}
            for date_data in curr_data:
                
                countries_data = date_data['geo_eCPMs']
                v_time = str(date_data['date'])
                chart_time = self.date2millis(v_time)
                
                for country_data in countries_data:
                    
                    countryCode = str(item['country'])
                    if countries and not countryCode in countries:
                        continue
                    
                    countryName = countryCode2Name(countryCode) 
                    revenue = float(country_data['revenue'])
                    index = days_array.index(chart_time)
                    
                    if not _json.has_key(countryName):
                        _json[countryName] = {}
                        _json[countryName]['key'] = countryName
                        _json[countryName]['values'] = [ [i,0] for i in days_array ]
                        _json[countryName]['total'] = 0
                    _json[countryName]['values'][index][1] += revenue
                    _json[countryName]['total'] += revenue
            return _json
    
    def vungle2json_generic(self, curr_data,countries,since,until):
        days_array = get_days_array(since,until)
        
        _json = {'key':'vungle', 'values':[ [i,0] for i in days_array ], 'total':0 }
        for date_data in curr_data:
            
            countries_data = date_data['geo_eCPMs']
            v_time = str(date_data['date'])
            chart_time = self.date2millis(v_time)
            
            for country_data in countries_data:
                
                countryCode = str(item['country'])
                if countries and not countryCode in countries:
                    continue
                
                countryName = countryCode2Name(countryCode) 
                revenue = float(country_data['revenue'])
                index = days_array.index(chart_time)
                _json['values'][index][1] += revenue
                _json['total'] += revenue
        return _json
    
    def date2millis(self,v_time):
        tt = datetime.datetime.strptime(v_time, "%Y-%m-%d")
        t = time.mktime(tt.timetuple())
        return int(t*1000)
    
    
    
    
    
    