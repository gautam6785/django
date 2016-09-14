from generic import generic_service
from apiclient.discovery import build
from oauth2client import client
from datetime import datetime as DT, timedelta as TD
from oauth2client.client import Credentials
from ad_revenues.ad_revenues import get_user_creds, is_duplicate_platform ,date2timestamp, round_timestamp, get_days_array
import httplib2, os, json, traceback, sys
from django.http import HttpResponse, Http404, JsonResponse
import time,datetime
from core.currency import convert_decimal_to_usd
REFRESH_MINS = 15
_file =  os.path.dirname(os.path.realpath(__file__)) + '/../secrets/admob.secret'
    
class adx_service(generic_service):


    def signup(self, request):
        try:            
            #auth_uri = get_auth_uri()
            auth_uri = self.get_auth_uri()
            redirection = {"url": auth_uri}
            return HttpResponse(json.dumps(redirection)) 
        except:
            #traceback.print_exc(file=sys.stdout)
            return HttpResponse("0")

    def get_flow(self):
        flow = client.flow_from_clientsecrets(
                _file,
                scope='https://www.googleapis.com/auth/adexchange.seller.readonly',
                redirect_uri='http://'+self.HOSTNAME+'/ad-revenues/adx_callback'
        )
        flow.params['access_type'] = 'offline'
        #flow.params['approval_prompt'] = 'force'
        return flow
    
    def get_auth_uri(self):
        flow = self.get_flow()
        auth_uri = flow.step1_get_authorize_url()
        #print auth_uri
        return auth_uri
    
    def get_credentials(self, code):
        flow = self.get_flow()
        credentials = flow.step2_exchange(code)
        #print credentials.to_json()
        return credentials
    
    
    def get_http_auth(self, user):
        
        c = get_user_creds(user, 'adx')
        credentials = c.content_object.credential
        return self.get_http_auth_by_cred(credentials)
        
    def get_http_auth_by_cred(self, credentials):
        credentials_json = credentials.to_json()
        new_creds = Credentials.new_from_json(credentials_json)
        if (new_creds.token_expiry - DT.utcnow()) < TD(minutes=REFRESH_MINS):
            new_creds.refresh(httplib2.Http())
        new_creds.authorize(httplib2.Http())
        http_auth = credentials.authorize(httplib2.Http())
        
        return http_auth
    
    
    def get_all_apps_names(self,credentials):
        try:
            http_auth = self.get_http_auth_by_cred(credentials.credential)
            
            drive_service = build('adexchangeseller', 'v2.0', http=http_auth)
            MAX_PAGE_SIZE = 50

            request = drive_service.accounts().list(maxResults=MAX_PAGE_SIZE)
            accounts_ids = []
            while request is not None:
                result = request.execute()
                accounts = result['items']
                for account in accounts:
                    accounts_ids.append(account['id'])
                request = drive_service.accounts().list_next(request, result)

            reports = []
            startDate = 'today-1d'
            endDate   = 'today'
            
            for account_id in accounts_ids:
                report = drive_service.accounts().reports().generate(
                accountId=account_id,
                startDate=startDate,
                endDate=endDate,
                dimension=['MOBILE_APP_NAME', 'DOMAIN_NAME' ],
                metric=['CLICKS'],
                filter=["PRODUCT_NAME==Mobile In-App"]
                ).execute()
                reports.append(report)
            
            names = []
            for report in reports:
                if 'rows' in report:
                    for row in report['rows']:
                        names.append( {'name':row[0],
                                       'platform':' ',
                                       'id': row[1],
                                    })
            names.sort(key=lambda x: x['name'])
            
            return names
        except:
            #traceback.print_exc(file=sys.stdout)
            return []
        
        
    
    def produce_chart_json(self, user, app_id, breakdown, countries, since=0, until=0):
        http_auth = self.get_http_auth(user)
                
        since = round_timestamp(since)
        until = round_timestamp(until)
        
        if breakdown == 'country':
            dimension = ['COUNTRY_NAME', 'DATE']
        elif breakdown == 'platform':
            dimension = ['DATE']
        else:
            dimension = []
        data = self.get_adx_revenues(http_auth, app_id, dimension, countries, since, until)
        currency = self.get_currency(http_auth)
        conversion = float(convert_decimal_to_usd(1,currency))
        if breakdown == 'country':
            _json = self.adx2json(data, conversion, since, until)
        elif breakdown == 'platform':
            _json = self.adx2json_generic(data, conversion, since, until)
        else:
            _json = {}
            
        return _json
    
    def get_assets_count(self, credentials):
        names = self.get_all_apps_names(credentials)
        return len(names)
    
    def get_status(self, credentials):
        return "Connected"
    
    def get_total_ad_revenues_by_country(self, user, app_id, countries=[], since=0, until=0):
        indexes = {'COUNTRY_CODE':0, 'EARNINGS':1}
        http_auth = self.get_http_auth(user)
        
        dimension = ['COUNTRY_CODE'] 
        data = self.get_adx_revenues(http_auth, app_id, dimension, countries, since, until)
        
        _json = {}
        for d in data:
            if 'rows' in data:
                rows = d['rows']
                for row in rows:
                    country = str(row[indexes['COUNTRY_CODE']])
                    value = float(row[indexes['EARNINGS']])
                    if not country in _json:
                        _json[country] =  value
                    else:
                        _json[country] += value
            else:
                print "no rows: ", data
                
        return _json
    
    def date2millis(self, dt):
        tt = datetime.datetime.strptime(dt, "%Y-%m-%d")
        t = time.mktime(tt.timetuple())
        return int(t*1000)    
    
    
    
    def get_adx_revenues(self, http_auth, app_id='', dimension=[], countries=[], since=0, until=0):
        drive_service = build('adexchangeseller', 'v2.0', http=http_auth)
        MAX_PAGE_SIZE = 50
        
        request = drive_service.accounts().list(maxResults=MAX_PAGE_SIZE)
        accounts_ids = []
        while request is not None:
            result = request.execute()
            accounts = result['items']
            for account in accounts:
                accounts_ids.append(account['id'])
            request = drive_service.accounts().list_next(request, result)
        
        reports = []
        if app_id:
                filter = ['DOMAIN_NAME==' + app_id]
        else:
                filter = []
        if countries != []:
            country_list = ''
            for country in countries:
                country_list += country+","
            filter.append('COUNTRY_CODE=='+str(country_list))
            
        startDate = date2timestamp(since)
        endDate   = date2timestamp(until)
        
        for account_id in accounts_ids:
            report = drive_service.accounts().reports().generate(
              accountId=account_id, startDate=startDate, endDate=endDate,
              filter=filter,
              metric=['EARNINGS'],
              dimension=dimension,
              ).execute()
            reports.append(report)
        return reports
    

    
    def adx2json(self, data, conversion, since=0, until=0):
        indexes = {'COUNTRY_NAME':0, 'DATE':1, 'EARNINGS':2}
        _json = {}
        
        days_array = get_days_array(since,until)
        
        for d in data:
            if not 'rows' in d:
                continue
            
            rows = d['rows']
            for row in rows:
                    country = row[indexes['COUNTRY_NAME']].encode('utf-8')
                    if not _json.has_key(country):
                            _json[country] = {
                                    "values": [ [i,0] for i in days_array ],
                                    "key": country,
                                    "total": 0,
                            }
                    timestamp = self.date2millis(row[indexes['DATE']].encode('utf-8'))
                    value = float(row[indexes['EARNINGS']]) * conversion
                    index = days_array.index(timestamp)
                    _json[country]["values"][index][1] = value
                    _json[country]["total"] += value
        return _json
    
    def adx2json_generic(self, data, conversion, since=0, until=0):
        indexes = {'DATE':0, 'EARNINGS':1}
        _json = {}
        
        days_array = get_days_array(since,until)
        _json = {'key':'adx', 'total':0, "values": [ [i,0] for i in days_array ]}
        
        for d in data:
            if not 'rows' in d:
                continue
            rows = d['rows']
            for row in rows:
                timestamp = self.date2millis(row[indexes['DATE']].encode('utf-8'))
                value = float(row[indexes['EARNINGS']]) * conversion
                index = days_array.index(timestamp)
                _json["values"][index][1] = value
                _json["total"] += value
            return _json
    
    def get_currency(self, http_auth):
        drive_service = build('adexchangeseller', 'v2.0', http=http_auth)
        MAX_PAGE_SIZE = 50
        
        request = drive_service.accounts().list(maxResults=MAX_PAGE_SIZE)
        accounts_ids = []
        while request is not None:
            result = request.execute()
            accounts = result['items']
            for account in accounts:
                accounts_ids.append(account['id'])
            request = drive_service.accounts().list_next(request, result)
        
        reports = []
        
        startDate = 'today'
        endDate   = 'today'
        
        for account_id in accounts_ids:
            report = drive_service.accounts().reports().generate(
              accountId=account_id, startDate=startDate, endDate=endDate,
              metric=['EARNINGS'],
              ).execute()
            reports.append(report)
        
        currency = 'USD'
        
        if reports:
            report = reports[0]
            headers = report['headers']
            for header in headers:
                if 'currency' in header:
                    currency = header['currency']
                    
                
            
        return currency
            

    def validate(self, credentials):
        ### for now: static value
        return True
    





    
        
        
        
        
        
        
        
        
        
        
        
        