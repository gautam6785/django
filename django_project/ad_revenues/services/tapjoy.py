from generic import generic_service
import requests
import json
import traceback,sys
import time,datetime
from ad_revenues.ad_revenues import get_user_creds, round_timestamp, date2timestamp, get_days_array, countryCode2Name
from ad_revenues.models import tapjoy_credentials, credentials
from django.http import HttpResponse, Http404, JsonResponse

tapjoy_urls = {
    'validate'          : 'https://api.tapjoy.com/reporting_data.json',
    'applications'      : 'https://api.tapjoy.com/reporting_data.json',
    'single_app'        : 'https://rpc.tapjoy.com/api/v1/exports',
    }

class tapjoy_service(generic_service):
    
    def get_api_key(self, user):
        c = get_user_creds(user,'tapjoy')
        return str(c.content_object.api_key)
    
    def signup(self,request):
        
        r = request.POST
        try:
                email=r.get('email')
                api_key = r.get('api_key')
                valid = self.tapjoy_validate(email, api_key)
                if valid:
                        vc = tapjoy_credentials(
                          email = email,
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
    
    def tapjoy_request(self, url, params):
        res = requests.get(url, params=params)
        return res
        
    def get_all_apps_names(self,credentials):
        try:
            api_key = credentials.api_key
            email = credentials.email
            date = date2timestamp(time.time())
            url = tapjoy_urls['applications']
            params = {"api_key": api_key, "email": email, "date": date}
            
            curr_page = 1
            total_pages = 1
            apps = []
            while curr_page <= total_pages:
                params['page'] = curr_page
                curr_page += 1
                res = self.tapjoy_request(url, params)
                if res.status_code == 200:
                    response = json.loads(res.text)
                    response_apps = response['Apps']
                    total_pages = int(response['TotalPages'])
                    
                    for app in response_apps:
                        a = {'name': app['Name'], 'id':app['AppKey'], 'platform':app['Platform']}
                        apps.append(a)
                else:
                    continue
            return apps
        except:
            #traceback.print_exc(file=sys.stdout)
            return []
 
 
    def tapjoy_validate(self, email, api_key):
        ## will try to fetch the applications list of the user          ##
        ## if json object is returned then the credentials are valid    ##
        url = tapjoy_urls['validate']
        date = date2timestamp(time.time())
        params = {"api_key": api_key, "email": email, "date": date}
        res = requests.get(url, params=params)
        if res.status_code == 200:
            return True
        return False
    
    
    
    
    
    