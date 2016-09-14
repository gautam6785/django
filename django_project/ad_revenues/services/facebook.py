from generic import generic_service
import requests, json
import urllib
import hashlib
import hmac
import time, datetime
from ad_revenues.ad_revenues import get_user_creds, round_timestamp, get_days_array, countryCode2Name
from django.http import HttpResponse, Http404, JsonResponse

FB_APP_ID = '127165434364597'
FB_APP_SECRET = '732252cfac28d8242beb2e827c893237'

class facebook_service(generic_service):

    def get_status(self, credentials):
        return "Missing Permissions"
    
    def signup(self, request):
        try:
            url = self.auth_redirect()
            redirection = {"url": url }
            return HttpResponse(json.dumps(redirection))
        except:
            #traceback.print_exc(file=sys.stdout)
            return HttpResponse("0")

    def auth_redirect(self):
        auth_url = 'https://facebook.com/dialog/oauth'
        data = {
            'app_id' :FB_APP_ID,
            'scope' : ['read_audience_network_insights','ads_management'],
            'redirect_uri' : 'http://'+self.HOSTNAME+'/ad-revenues/facebook_callback',
            }
        url = auth_url +"?"+ urllib.urlencode(data)
        return url 
    
    
    def code_to_token(self,code):
        auth_url = 'https://graph.facebook.com/oauth/access_token'
        data = {
            'client_id': FB_APP_ID,
            'client_secret': FB_APP_SECRET,
            'redirect_uri': 'http://'+self.HOSTNAME+'/ad-revenues/facebook_callback',
            'code':code,
            }
        res = requests.get(auth_url, params=data)
        return res 
    
    def parse_facebook_callback(self, text):
        lines = text.split("&")
        obj = {}
        for line in lines:
            kv = line.partition("=")
            obj[kv[0]] = kv[2]
        return obj
    
    
    def produce_chart_json(self, user, app_id, breakdownBy, countries, since=0, until=0):
        token = self.get_token(user)

        since = round_timestamp(since)
        until = round_timestamp(until)
        
        curr_data = self.app_revenues_by_country(token, app_id, since,until+86400)
        mul2dolar = self.get_usd_exchange_inverse(token)
        if breakdownBy == 'country':
            chartData = self.facebook2json(curr_data,mul2dolar,countries,since,until)
        elif breakdownBy == 'platform':
            chartData = self.facebook2json_generic(curr_data,mul2dolar,countries,since,until)
        else:
            chartData = {}
        
        fb_data = {}
        fb_data["chartData"] = chartData
        return chartData
    
    
    def get_all_apps(self,credentials): 
        # get all add accounts
        ### for each account get it's applications 
          # using graph.facebook.com/{ad-account}/applications ##
        token = credentials.token
        secret_proof = genAppSecretProof(token,FB_APP_SECRET)
        req_uri = 'https://graph.facebook.com/v2.6/me/adaccounts'
        data = {
            'access_token': token,
            'appsecret_proof':secret_proof,
        }
        ad_accounts_str = requests.get(req_uri, params=data)
        tojson = json.loads(ad_accounts_str.text)
        adaccounts = tojson['data']
        
        acc1 = adaccounts[0]['id']
        req_uri = 'https://graph.facebook.com/v2.6/'+acc1+'/applications'
        data = {
            'access_token': token,
            'appsecret_proof':secret_proof,
        }
        apps_str = requests.get(req_uri, params=data)
        
        return {}
    
    def get_all_apps_names(self,credentials):
        self.get_all_apps(credentials)
        return []

    def get_token(self,user):
        c = get_user_creds(user,'facebook')
        return c.content_object.token

    def app_revenues_by_country(self, token, app_id, since, until, period='daily'):
        req_uri = 'https://graph.facebook.com/v2.5/' +app_id+ '/app_insights/app_event/'
        secret_proof = genAppSecretProof(token,FB_APP_SECRET)
        data = {
            'since': since,
            'until': until,
            'period': period,
            'event_name':'fb_ad_network_revenue',
            'aggregateBy':'SUM',
            'access_token': token,
            'appsecret_proof':secret_proof,
            'breakdowns[]':['country'],
        }
        revenues = requests.get(req_uri, params=data)
        return json.loads(revenues.text)
        
        
    def get_usd_exchange_inverse(self, token):
        req_uri = 'https://graph.facebook.com/v2.6/me?fields=currency'
        secret_proof = genAppSecretProof(token,FB_APP_SECRET)
        data = {
            'access_token': token,
            'appsecret_proof':secret_proof,
        }
        currency_data = requests.get(req_uri, params=data)
        currency_json = json.loads(currency_data.text)
        return currency_json['currency']['usd_exchange_inverse']
                                 
                                 
                                 
    def facebook2json(self, curr_data, mul2dolar, countries, since=0, until=0, top5=[]):
        temp = curr_data
        _json = {}
        days_array = get_days_array(since,until)
        
        temp = temp['data']
        for entry in temp:
                country = str(entry['breakdowns']['country'])
                if countries and not country in countries:
                    continue
                countryName = countryCode2Name(country)
                fb_time = str(entry['time'])
                earned = float(entry['value'])
                if not _json.has_key(countryName):
                        _json[countryName] = {
                                'key': countryName,
                                'values': [ [i,0] for i in days_array ],
                                'total': 0,
                        }
                chart_time = fb_date2millis(fb_time)
                index = days_array.index(chart_time)
                _json[countryName]['values'][index][1] = earned
                _json[countryName]['total'] += earned
        return _json
    
    def facebook2json_generic(self, curr_data, mul2dolar, countries, since=0, until=0, top5=[]):
        days_array = get_days_array(since,until)
        max_time = 0
        _json = {'key':'facebook', 'values':[ [i,0] for i in days_array ], 'total':0 }
        temp = curr_data['data']
        for entry in temp:
            country = str(entry['breakdowns']['country'])
            if countries and not country in countries:
                continue
            fb_time = str(entry['time'])
            earned = float(entry['value'])
            
            chart_time = fb_date2millis(fb_time)
            max_time = max(chart_time,max_time)
            index = days_array.index(chart_time)
            _json['values'][index][1] += earned
            _json['total'] += earned
        return _json    
    
    def get_total_ad_revenues_by_country(self, user, app_id, countries=[], since=0, until=0):
        token = self.get_token(user)

        since = round_timestamp(since)
        until = round_timestamp(until)
        
        curr_data = self.app_revenues_by_country(token, app_id, since,until+86400)

        _json = {}
        temp = curr_data['data']
        for entry in temp:
            country = str(entry['breakdowns']['country'])
            if countries and not country in countries:
                continue
            earned = float(entry['value'])
            if not country in _json:
                _json[country] =  earned
            else:
                _json[country] += earned
            
        return _json
    
    
def facebook_code_to_token(code):
    auth_url = 'https://graph.facebook.com/oauth/access_token'
    data = {
        'client_id': FB_APP_ID,
        'client_secret': FB_APP_SECRET,
        #'redirect_uri': 'http://www.evyatar.com:7449/ad-revenues/facebook_callback',
        'redirect_uri': 'http://'+HOSTNAME+'/ad-revenues/facebook_callback',
        'code':code,
        }
    res = requests.get(auth_url, params=data)
    return res 

def get_user_by_token(token):
    req_uri = 'https://graph.facebook.com/me'
    secret_proof = genAppSecretProof(token, FB_APP_SECRET)
    data = {
        'access_token' : token,
        'appsecret_proof':secret_proof,
        }
    me = requests.get(req_uri, params=data)
    
    return me.text
    

def calc_revenue_percentage(curr, prev):
        try:
                return 100 - round((float(curr)/float(prev))*100)
        except:
                return json.dumps(float('nan'))

def calc_diff_percentage(curr, prev):
        pass
        
def fb_calc_revenue_data(curr_data, prev_data):
        rev_data = {}
        for item in curr_data:
                countryCode = str(item['breakdowns']['country'])
                temp = {}
                temp["currentTotal"]  = str(item['value'])
                temp["country_code"]  = countryCode
                temp["name"]          = countryCode2Name(countryCode)
                rev_data[countryCode] = temp
                ###################################################
                ## TODO: add "totalPercentage" ########## #########
                ###################################################
        for item in prev_data:
                countryCode = str(item['breakdowns']['country'])
                if not rev_data.has_key(countryCode):
                        continue
                currentTotal  = rev_data[countryCode]["currentTotal"]
                previousTotal = str(item['value'])
                rev_data[countryCode]["previousTotal"] = previousTotal
                rev_percentage = calc_revenue_percentage(currentTotal, previousTotal)
                rev_data[countryCode]["revenuePercentage"] = rev_percentage
                rev_data[countryCode]['color'] = getColor(rev_percentage) 
        return rev_data.values()
    

def fb_app_data(token, app_id):
        req_uri = 'https://graph.facebook.com/v2.5/' + app_id
        secret_proof = genAppSecretProof(token,FB_APP_SECRET)
        data = {
                'access_token': token,
                'appsecret_proof':secret_proof,
        }
        info = requests.get(req_uri, params=data)
        return json.loads(info.text)

def fb_total_app_revenue(token, app_id, from_month_back, to_month_back):
    req_uri = 'https://graph.facebook.com/v2.5/' +app_id+ '/app_insights/app_event/'
    secret_proof = genAppSecretProof(token,FB_APP_SECRET)
    data = {
        'since': from_month_back,
        'until': to_month_back,
        'period': 'range',
        'event_name':'fb_ad_network_revenue',
        'aggregateBy':'SUM',
        'access_token': token,
        'appsecret_proof':secret_proof,
    }
    revenues = requests.get(req_uri, params=data)
    return json.loads(revenues.text)
    
def fb_date2millis(fb_time):
        fb_time = fb_time[:10]
        tt = datetime.datetime.strptime(fb_time, "%Y-%m-%d")
        t = time.mktime(tt.timetuple())
        return int(t*1000)
    
def genAppSecretProof(access_token,app_secret):
    h = hmac.new (
        app_secret.encode('utf-8'),
        msg=access_token.encode('utf-8'),
        digestmod=hashlib.sha256
    )
    return h.hexdigest()