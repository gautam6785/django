from django.conf.urls import patterns, url
from dashboard import views

urlpatterns = [
  url(r'^$', views.main_dashboard, name='dashboard'),
  #url(r'^apps/(?:platform_id/(?P<platform_id>\d+)?:page/(?P<page>\d+)/)?$',views.apps, name='apps'),
  url(r'^apps/$',views.apps, name='apps'),
  #url(r'^apps/platform_type_id/(?P.*?)/$',views.apps,name='apps'),
  url(r'^app_details/(?P<app_id>.+)/$', views.app_details, name='app_details'),
  url(r'^app_list/(?P<platform_type>.+)/(?P<start_in_seconds>.+)/(?P<end_in_seconds>.+)/$', views.app_list),
  url(r'^app_revenue/(?P<app_id>.+)/(?P<country_ids>.+)/$', views.app_revenue, name='app_revenue'),
  url(r'^app_download/(?P<app_id>.+)/(?P<country_ids>.+)/$', views.app_download, name='app_download'),
  url(r'^app_info/(?P<bundle_id>.+)/$', views.app_info),
  url(r'^app_info_android/(?P<app_id>.+)/$', views.app_info_android),
  url(r'^get_products/$', views.products),
  #url(r'^app_details/(?P<platform>.+)/(?P<country>.+)/(?P<app_id>.+)/$', views.app_details),
  url(r'^get_products/$', views.products),
  url(r'^get_country_list/$', views.get_country_list),
  url(r'^graph_data_app/(?P<country_ids>.+)/(?P<app_id>.+)/(?P<start_in_seconds>.+)/(?P<end_in_seconds>.+)/$', views.graph_app_ranks_data_with_range),
  url(r'^graph_data_app_download/(?P<country_ids>.+)/(?P<app_id>.+)/(?P<start_in_seconds>.+)/(?P<end_in_seconds>.+)/$', views.app_download_graph_data_with_range),
]
