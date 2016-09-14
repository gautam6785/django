import logging


from django.http import HttpResponse
from django.shortcuts import render, redirect
import django.conf

import dashboard

from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required

from django.core.urlresolvers import reverse
from django.contrib.auth.views import password_reset, password_reset_confirm

logger = logging.getLogger(__name__)
 
def homepage(request):
    if request.user.is_authenticated():
        return dashboard.views.main_dashboard(request) 	
    #return render(request, "home.html")
    return redirect("/accounts/login")