from generic import generic_service
import requests
import json
import traceback,sys
import time,datetime
from ad_revenues.ad_revenues import get_user_creds, round_timestamp, get_days_array, countryCode2Name
from ad_revenues.models import adcolony_credentials, credentials
from django.http import HttpResponse, Http404, JsonResponse

adcolony_urls = {
    'general'      : 'http://clients.adcolony.com/api/v2/publisher_summary',
    }

class adcolony_service(generic_service):
    
    STARTYEAR = 2010
    
    def get_api_key(self, user):
        c = get_user_creds(user,'adcolony')
        return get_api_key_by_creds(c)
    
    def get_api_key_by_creds(c):
        return str(c.content_object.api_key)
    
    def signup(self,request):
        
        r = request.POST
        try:
                name=r.get('display_name')
                api_key = r.get('api_key')
                valid = self.adcolony_validate(api_key)
                if valid:
                        adc = adcolony_credentials(
                          name = name,
                          api_key = api_key,
                        )
                        adc.save()
                        gc=credentials(user=request.user,content_object=adc)
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
            url = adcolony_urls['general']
            
            responses = []
            date = format_date(time.time())
            year = int(date[-4:])
            mmdd= date[:-4]
            while year > self.STARTYEAR:
                start_date = mmdd+str(year-1)
                end_date = mmdd+str(year)
                year -=1
                params = {
                            "user_credentials": api_key, 
                            "group_by":"app",
                            "date": start_date, 
                            "end_date": end_date,
                          }
                res = requests.get(url, params=params)
                if res.status_code == 200:
                    responses.append(res)
            
            apps = {}
            for res in responses:
                try:
                    response = json.loads(res.text)
                    app_list = response['results']
                    for app in app_list:
                        app_id = app['app_id']
                        a = {'name': app['app_name'], 'id':app['app_id'], 'platform':app['platform']}
                        apps[app_id] = a
                except:
                    continue
                    #print res.text
                    #traceback.print_exc(file=sys.stdout)
            return apps.values()
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
            chartData = self.adcolony2json(curr_data_by_country,countries,since,until)
        elif breakdown == 'platform':
            chartData = self.adcolony2json_generic(curr_data_by_country,countries,since,until)
        else:
            chartData = {}
            
        cb_data = {}
        cb_data["chartData"] = chartData
        return cb_data["chartData"]
    
    def get_app_revenues(self, api_key , appId, since, until):
        since = adjustDate(since,until)
        data = {
            'user_credentials': api_key,
            'date': format_date(since),
            'date_group': 'day',
            'end_date': format_date(until),
            'group_by': 'country,app',
            'app_id': appId
            }
            
        url = adcolony_urls['general']
        response = requests.get(url, params=data)
        try:
            _json = json.loads(response.text)
        except:
            _json = {}
            print "In get_app_revenues: JSON Object could not be decoded:"
            print _json
                
        return _json
    
    
    def get_total_ad_revenues_by_country(self, user, app_id, countries=[], since=0, until=0):
        api_key = self.get_api_key(user)
        
        since = round_timestamp(since)
        until = round_timestamp(until)
        
        _json = {}
        curr_data_by_country = self.get_app_revenues(api_key , app_id, since, until)
        if 'results' in curr_data_by_country:
            results = curr_data_by_country['results']
        else:
            results = []
            
        for entry in results:
            
            countryCode = entry['country']
            ac_time = str(entry['date'])
            chart_time = self.date2millis(ac_time)
            
            if countries and not countryCode in countries:
                continue
            
            countryName = countryCode2Name(countryCode)
            revenue = float(entry['earnings'])
            if not _json.has_key(countryName):
                _json[countryName] =  revenue
            else:
                _json[countryName] += revenue
        return _json
    
    def adcolony_validate(self,api_key):
        ## will try to fetch the applications list of the user ##
        url = adcolony_urls['general']
        params = {"user_credentials": api_key, "date":format_date(time.time()) }
        res = requests.get(url, params=params)
        #print res.text
        if res.status_code !=  200:
            return False
        try:
            jres = json.loads(res.text)
            if jres['status'] != "success":
                return False
            return True
        except:
            return False
        
    def validate(self, credentials):
        api_key = credentials.api_key
        return self.adcolony_validate(api_key)
    
    def adcolony2json(self, curr_data, countries, since, until):
        days_array = get_days_array(since,until)
        app_data = curr_data['results']
        _json = {}
        
        for entry in app_data:
            
            countryCode = entry['country']
            ac_time = str(entry['date'])
            chart_time = self.date2millis(ac_time)
            
            if countries and not countryCode in countries:
                continue
            
            countryName = countryCode2Name(countryCode) 
            if not _json.has_key(countryName):
                _json[countryName] = {}
                _json[countryName]['key'] = countryName
                _json[countryName]['values'] = [ [i,0] for i in days_array ]
                _json[countryName]['total'] = 0
                
            revenue = float(entry['earnings'])
            index = days_array.index(chart_time)
            _json[countryName]['values'][index][1] = revenue
            _json[countryName]['total'] += revenue
            
        return _json
    
    def adcolony2json_generic(self, curr_data,countries,since,until):

        days_array = get_days_array(since,until)
        _json = {'key':'adcolony', 'values':[ [i,0] for i in days_array ], 'total':0 }
        
        try:
            app_data = curr_data['results']
        except:
            app_data = []
            print curr_data
        for entry in app_data:
            
            ac_time = str(entry['date'])
            chart_time = self.date2millis(ac_time)
            countryCode = str(entry['country'])
            
            if countries and not countryCode in countries:
                continue
            
            countryName = countryCode2Name(countryCode) 
            revenue = float(entry['earnings'])
            index = days_array.index(chart_time)
            _json['values'][index][1] += revenue
            _json['total'] += revenue
        return _json
    
    def date2millis(self,v_time):
        tt = datetime.datetime.strptime(v_time, "%Y-%m-%d")
        t = time.mktime(tt.timetuple())
        return int(t*1000)
  
MAX_DAYS = 84
def adjustDate(since,until):
    # adjustDate - check if since is more then 40 days ago
    #if it is , return date of 40 days ago
    dlt = datetime.timedelta(seconds=until-since)
    days = dlt.days
    if days >= MAX_DAYS :
        maxdays = datetime.timedelta(days=MAX_DAYS )
        since = until - maxdays.total_seconds()
    print "adjust: ", since
    return since

def format_date(ts):
    dt = datetime.datetime.fromtimestamp(ts)
    return dt.strftime('%m%d%Y')  
    