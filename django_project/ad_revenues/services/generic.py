from django.conf import settings

class generic_service:

    HOSTNAME = settings.HOSTNAME
    
    

    def signup(request):
        return 0
    
    def get_all_apps_names(self,credentials):
        return []
    
    def produce_chart_json(self, user, app_id, breakdown, countries, since=0, until=0):
        return {}
    
    def get_assets_count(self, credentials):
        names = self.get_all_apps_names(credentials)
        return len(names)
    
    def get_status(self, credentials):
        if self.validate(credentials):
            return "Connected"
        else:
            return "Invalid Credentials"
    
    def get_total_ad_revenues_by_country(self, user, app_id, countries=[], since=0, until=0):
        return {}
    
    def validate(self, credentials):
        return False