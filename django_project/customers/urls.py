from django.conf.urls import patterns, url
from customers import views
urlpatterns = [
    url(r'^update_sales_reports_account/$', views.update_sales_reports_account),
    url(r'^delete_sales_reports_account/$', views.delete_sales_reports_account),
    url(r'^get_2_step_verification_page/$', views.get_2_step_verification_page),
    url(r'^step2_verification/$', views.step2_verification),
    url(r'^itunes_login/', views.itunes_login),
    url(r'^google_login/', views.google_login)
]
