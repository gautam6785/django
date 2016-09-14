from django.conf.urls import patterns, url
from download import views
urlpatterns = [
    url(r'^single_app_revenue/', views.single_app_revenue),
    url(r'^get_app_sku/', views.get_app_sku),
    url(r'^reports/', views.reports),
    url(r'^sales_reports/', views.sales_reports),
    url(r'^itunes_reports/', views.itunes_reports),
    url(r'^test_query/', views.test_query),
    url(r'^big_query/', views.big_query),
    url(r'^gcloud/', views.gcloud),
    url(r'^appinfo/', views.appinfo),
    url(r'^app_list/', views.app_list),
    url(r'^install_reports/', views.install_reports),
    url(r'^send_email/', views.send_email_message),
]
