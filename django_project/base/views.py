from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.shortcuts import render_to_response
from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext
from django.contrib.auth.models import User
from django.contrib.auth import logout, login, authenticate
from django.contrib import messages
from django.core.cache import cache
from django import forms


def custom_error(request, template_name="500.html"):
    return render_to_response(template_name, {}, context_instance=RequestContext(request))

def custom_404(request, template_name="404.html"):
    return render_to_response(template_name, {}, context_instance=RequestContext(request))

