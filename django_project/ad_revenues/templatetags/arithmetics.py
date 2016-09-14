from django import template
from django.conf import settings

register = template.Library()


def multiply(value, arg):
        return value*arg


def divide(value, arg):
        return value/arg

def roundNum(value, by):
    try:
        return round(value,by)
    except:
        return 0
    
register.filter('divide', divide)
register.filter('multiply', multiply)
register.filter('round', roundNum)
