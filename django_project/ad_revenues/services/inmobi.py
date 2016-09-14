from generic import generic_service
import requests
import json
import traceback,sys
import time,datetime
from ad_revenues.ad_revenues import get_user_creds, round_timestamp, get_days_array, countryCode2Name
from ad_revenues.models import inmobi_credentials, credentials
from django.http import HttpResponse, Http404, JsonResponse

urls = {
    'general'      : 'https://api.inmobi.com/v1.1/reporting/publisher.json',
    'session'      : 'https://api.inmobi.com/v1.0/generatesession/generate',
    }

class inmobi_service(generic_service):
        
    def get_credentials(self, user):
        c = get_user_creds(user,'inmobi')
        return c.content_object
    
    
    def generate_session_token(self, email, password, api_key):
        
        url = urls['session']
        headers = {'userName': email,
                   'password': password,
                   'secretKey': api_key,
                   }
        res = requests.get(url, headers=headers)
        print "got session: \n", res.text, "\n#######################"
        if res.status_code == 200:
            _json = json.loads(res.text)
            if _json['error'] == False:
                accountID = _json['respList'][0]['accountId']
                sessionId = _json['respList'][0]['sessionId']
                return [accountID,sessionId]
            else:
                return []
        else:
            return []
              
    
    
    def signup(self,request):
        
        r = request.POST
        try:
                email=r.get('email')
                password=r.get('password')
                api_key = r.get('api_key')
                
                session_data = self.generate_session_token(email, password, api_key)
                if session_data:
                    account_id, session_id = session_data
                    valid = True
                else:
                    print 'could not extract session id'
                    raise Exception("could not extract session id")
                
                if valid:
                        inc = inmobi_credentials(
                          email = email, 
                          password = password,
                          api_key = api_key,
                          account_id = account_id,
                          session_id = session_id,
                        )
                        inc.save()
                        gc=credentials(user=request.user,content_object=inc)
                        gc.save()
                        res = {"message": "Account added successfully", "color": "green"}
                        return HttpResponse(json.dumps(res))
        except:
                #traceback.print_exc(file=sys.stdout)
                res = {"message": "Error occured while adding account", "color": "red"}
                return HttpResponse(json.dumps(res))
            
        res = {"message": "Invalid Account Credentials", "color": "red"}
        return HttpResponse(json.dumps(res))
    
    def update_session_id(self, credentials):
        email = credentials.email
        password = credentials.password
        api_key = credentials.api_key
        token = self.generate_session_token(email, password, api_key)
        if token:
            accountID,sessionId = token
            credentials.session_id = sessionId
            credentials.save()
    
    def inmobi_request(self, credentials, url, params):
        
        headers = {}
        headers['secretKey'] = credentials.api_key,
        headers['accountId'] = credentials.account_id,
        headers['sessionId'] = credentials.session_id,
        headers['Content-Type'] = 'application/json'
        
        res = requests.get(url, params=params, headers=headers)
        print "headers: \n", headers
        print "status: ", res.status_code ,":\n", res.text, "\n####################"
        
        if res.status_code == 200:
            _json = json.loads(res.text)
            
            ## session is expired: update session id 
            if _json['error'] == "true":
                print "error1"
                self.update_session_id(credentials)
                headers['sessionId'] = credentials.session_id,
                res = requests.get(url, params=params, headers=headers)
                
                if res.status_code == 200:
                    if _json['error'] != "true":
                        print "works1"
                        _json = json.loads(res.text)
                        return _json['respList']
                    print "error2"
                return {}
            
            ## session in valid : return resulsts
            return _json['respList']
        else:
            print "error in request"
            return {}
            
        
    def get_all_apps_names(self,credentials):
        try:
            url = urls['general']
            headers = {'Content-Type': 'application/json'}
            timeFrame = "{0}:{1}".format(format_date(time.time()-86400), format_date(time.time()))
        
            params = {
                #'metrics'  : ['earnings'],
                'groupBy'  : ['site'],
                'timeFrame': timeFrame,
                }
            
            entries = self.inmobi_request(credentials, url, params)
            
            apps = []
            for entry in entries:
                a = {'name': entry['siteName'], 'id':entry['siteId'], 'platform':entry['platform']}
                apps.append(a)
                
            return apps
        except:
            #traceback.print_exc(file=sys.stdout)
            return []
        
        
        
    def produce_chart_json(self, user, app_id, breakdown, countries, since=0, until=0):
        
        credentials = self.get_credentials(user)
        
        since = round_timestamp(since)
        until = round_timestamp(until)
        
        curr_data_by_country = self.get_app_revenues(credentials , app_id, since, until)
        
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
    
    
    def get_app_revenues(self, credentials , appId, since, until):
        since = adjustDate(since,until)
        
        timeFrame = "{0}:{1}".format(format_date(since), format_date(until))
        
        data = {
            'timeFrame': timeFrame, 
            'metrics': ['earnings'],
            'groupBy': ['country','date'],
            'filterBy': [
                            { 
                                "filterName": "siteId",
                                "filterValue": [appId],
                                "comparator": "in",
                            }
                        ],
            }
            
        url = urls['general']
        
        try:
            _json = self.inmobi_request(credentials, url, data)
        except:
            _json = {}
            #traceback.print_exc(file=sys.stdout)
            
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
        params = {"user_credentials": api_key}
        res = requests.get(url, params=params)

        if res.status_code !=  200:
            return False
        try:
            jres = json.loads(res.text)
            if jres['status'] != "success":
                return False
            return True
        except:
            return False
    
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
    return dt.strftime('%Y-%m-%d')  
    