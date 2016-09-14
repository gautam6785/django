import home.views
import authentication.views
from django.conf.urls import patterns, include, url
from django.contrib import admin
import debug_toolbar

admin.autodiscover()
urlpatterns = [
    url(r'^$', home.views.homepage),
    url(r'^accounts/signup/$', authentication.views.signup, name='signup'),
    url(r'^accounts/login/$',  authentication.views.signin, name='signin'),
    url(r'^accounts/reset/$',  authentication.views.reset, name='reset'),
    url(r'^accounts/logout/$', authentication.views.signout, name='signout'),
    url(r'^accounts/reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$', authentication.views.reset_confirm, name='password_reset_confirm'),
    url(r'^success/$', authentication.views.success, name='success'),
    url(r'^admin/', include(admin.site.urls)),
    #url(r'^account/', include('customers.urls')),
    url(r"^customers/", include("customers.urls")),
    url(r'^dashboard/', include('dashboard.urls')),
    url(r'^download/', include('download.urls')),
    url(r'^ad-revenues/', include('ad_revenues.urls')),
    
]
urlpatterns += [
	url(r'^__debug__/', include(debug_toolbar.urls)),
]

handler500 = 'base.views.custom_error'
handler400 = 'base.views.custom_404'
