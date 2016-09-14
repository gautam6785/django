from django.conf.urls import patterns, url
import views

urlpatterns = [
#add platform:
  url(r'^add-platform/$', views.add_platform, name='add_platform'),
  url(r'^signup/(?P<platform>.+)/$', views.platform_signup, name='platform_signup'),
#admob:
  url(r'^auth2callback/$',views.auth2callback, name='auth2callback'),
#adx:
  url(r'^adx_callback/$',views.adx_callback, name='adx_callback'),
#facebook:
  url(r'^facebook_callback', views.facebook_callback, name='facebook_callback'),
#adtech:
  #url(r'adtech/signup$', views.adtech_signup, name='adtech_signup'),
  #url(r'adtech/reports$', views.adtech_pull_reports, name='adtech_pull_reports'),
#generic urls:
  url(r'remove_platform/(?P<platform>.+)/$', views.remove_platform, name='remove_platform'),
  url(r'platform_connections/(?P<platform>.+)/$', views.platform_connections, name="platform_connections"),
  url(r'app_connections/(?P<app_id>.+)/$', views.app_connections, name="app_connections"),
  url(r'^app_revenues/(?P<app_id>.+)/(?P<country>.+)/$', views.app_revenues, name='ad_revenues'),
  url(r'^app_ad_revenues/(?P<app_id>.+)/(?P<countries>.+)/(?P<breakdownBy>.+)/(?P<since>.+)/(?P<until>.+)/$', views.app_ad_revenues, name='app_ad_revenues'),
  url(r'^connections/(?P<app_id>.+)/$', views.app_connections, name='app_connections'),
  url(r'^connect-app/(?P<platform>.+)/(?P<fid>.+)/$', views.connect_app, name='connect_app'),
  url(r'connect-app2platform/(?P<app_id>.+)/$', views.connect_app2platform, name="connect_app2platform"),
  url(r'^delete-connection/(?P<platform>.+)/(?P<fid>.+)/$', views.delete_connection, name='delete_connection'),
  
  #url(r'^google_downloads_and_revenues/(?P<app_id>.+)/(?P<start_in_seconds>.+)/(?P<end_in_seconds>.+)/$', views.get_google_downloads_and_revenues),
  #url(r'^itunes_downloads_and_revenues/(?P<app_id>.+)/$', views.itunes_downloads_and_revenues),
  #url(r'^total_ad_revenues_by_country/(?P<app_info_id>.+)/(?P<since>.+)/(?P<until>.+)/$', views.get_total_ad_revenues_by_country),
  #url(r'^arpu_data/(?P<app_info_id>.+)/(?P<since>.+)/(?P<until>.+)/$', views.get_arpu_data),
  url(r'^get_arpu_data/(?P<app_info_id>.+)/(?P<since>.+)/(?P<until>.+)/$', views.get_arpu_in_range, name="ARPU"),
  url(r'^arpu/(?P<app_info_id>.+)/$', views.app_arpu, name="ARPU"),
]
