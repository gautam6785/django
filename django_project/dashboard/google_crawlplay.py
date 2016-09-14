import logging
from bs4 import BeautifulSoup
import requests
import re
import urllib2
import urllib
from urllib2 import Request
import codecs
import json
import pickle
from datetime import datetime
from pytz import utc
import urllib2
from re import match
from dateutil import parser
from core.currency import convert_decimal_to_usd, symbol_to_currency_code
from decimal import Decimal
from core.db.constants import TEN_PLACES
logger = logging.getLogger(__name__)

_ANDROID_APP_DETAIL_URL = 'https://play.google.com/store/apps/details?id=%s'

def getPageAsSoup( url, post_values ):
    if post_values:
        data = urllib.urlencode( post_values )
        data = data.encode( character_encoding )
        req = urllib2.Request( url, data )
    else:
        req = url
    try:
        response = urllib2.urlopen( req )
    except urllib2.HTTPError as e:
        print( "HTTPError with: ", url, "\t", e )
        return None
    the_page = response.read()
    soup = BeautifulSoup(the_page,"lxml")

    return soup


def get_app_detail(app_str):
	g_app_url = _ANDROID_APP_DETAIL_URL % (app_str)
	app_details = {}
	soup = getPageAsSoup( g_app_url, None )
	
	app_details['title'] = title(soup)
	app_details['developer'] = developer(soup)
	app_details['version'] = version(soup)
	app_details['icon'] = icon(soup)
	app_details['date_published'] = datePublished(soup)
	app_details['category'] = category(soup)
	app_details['genre'] = category(soup)
	app_details['price'] = price(soup)
	app_details['description'] = description(soup)
	app_details['updated'] = updated(soup)
	app_details['operating_system'] = required_android_version(soup)
	app_details['content_rating'] = content_rating(soup)
	app_details['size'] = file_size(soup)
	app_details['install'] = install(soup)
	app_details['developer_website'] = developer_website(soup)
	app_details['developer_email'] = developer_email(soup)
	app_details['score'] = score(soup)
	app_details['reviews'] = reviews(soup)
	app_details['histogram_one'] = histogram_one(soup)
	app_details['histogram_two'] = histogram_two(soup)
	app_details['histogram_three'] = histogram_three(soup)
	app_details['histogram_four'] = histogram_four(soup)
	app_details['histogram_five'] = histogram_five(soup)
	app_details['screenshots'] = screenshots(soup)
	
	return app_details
	


def title(soup):
	try:
		title_div = soup.find( 'div', {'class':'document-title'} )
		title = title_div.find( 'div' ).get_text().strip()
	except AttributeError as e:
		return None
	return title

def version(soup):
	try:
		version_div = soup.find( 'div', {'itemprop' : 'softwareVersion'} )
		version = version_div.find('div').get_text().strip()
	except AttributeError as e:
		return None
	return version
		
def developer(soup):
	try:
		subtitle = soup.find( 'a', {'class' : 'document-subtitle primary'} )
		developer = subtitle.get_text().strip()
	except AttributeError as e:
		return None
	return developer

def category(soup):
	try:
		category_span = soup.find( 'span', {'itemprop' : 'genre'} )
		category = category_span.get_text()
	except AttributeError as e:
		return None
	return category

def icon(soup):
	try:
		icon = soup.find( 'img', {'class' : 'cover-image'} )
		icon_url = icon.get('src').strip()
	except AttributeError as e:
		return None
	return icon_url

def datePublished(soup):
	try:
		date_published_div = soup.find( 'div', {'itemprop' : 'datePublished'} )
		datePublished = date_published_div.get_text().strip()
		releaseDate = parser.parse(datePublished).replace(tzinfo=utc)
	except AttributeError as e:
		return None
	return releaseDate

def price(soup):
	try:
		price_meta = soup.find( 'meta', {'itemprop' : 'price'})
		app_price = price_meta.get_text()
	except AttributeError as e:
		return None
	return app_price


def description(soup):
	try:
		app_description = soup.find( 'div', {'itemprop' : 'description'})
		description = app_description
	except AttributeError as e:
		return None
	return description


def updated(soup):
	try:
		date_published_div = soup.find( 'div', {'itemprop' : 'datePublished'} )
		datePublished = date_published_div.get_text().strip()
	except AttributeError as e:
		return None
	return datePublished

def required_android_version(soup):
	try:
		operating_system = soup.find( 'div', {'itemprop' : 'operatingSystems'})
		operatingsystems = operating_system.get_text().strip()
	except AttributeError as e:
		return None
	return operatingsystems

def content_rating(soup):
	try:
		content_rating_div = soup.find( 'div', {'itemprop' : 'contentRating'} )
		content_rating = content_rating_div.get_text().strip()
	except AttributeError as e:
		return None
	return content_rating

def file_size(soup):
	try:
		file_size = soup.find( 'div', {'itemprop' : 'fileSize'} )
		size = file_size.get_text().strip()
	except AttributeError as e:
		return None
	return size

def install(soup):
	try:
		app_install = soup.find( 'div', {'itemprop' : 'numDownloads'} )
		install = app_install.get_text().strip()
	except AttributeError as e:
		return None
	return install

def developer_website(soup):
	try:
		for dev_link in soup.find_all( 'a', {'class' : 'dev-link'} ):
			if dev_link.get_text().strip() == "Visit website":
				dev_website = dev_link.get( 'href' ).strip()
				website = re.match(r'^https:\/\/www.google.com\/url\?q=([^&]+)/', dev_website).group(1)
	except AttributeError as e:
		return None
	return website

def developer_email(soup):
	try:
		for dev_link in soup.find_all( 'a', {'class' : 'dev-link'} ):
			if dev_link.get_text().strip() != "Visit website":
				dev_email = dev_link.get( 'href' ).strip()
				email = re.match(r'^mailto:(.+)$', dev_email).group(1)
	except AttributeError as e:
		return None
	return email

def score(soup):
	try:
		app_score = soup.find( 'div', {'class' : 'score'} )
		score = app_score.get_text().strip()
	except AttributeError as e:
		return None
	return float(score)

def reviews(soup):
	try:
		app_reviews = soup.find( 'span', {'class' : 'reviews-num'} )
		Appreviews = app_reviews.get_text().strip()
		reviews = Appreviews.replace(',','')
	except AttributeError as e:
		return None
	return int(reviews)


def histogram_five(soup):
	try:
		app_reviews = soup.find( 'div', {'class' : 'rating-histogram'} )
		app_five = app_reviews.find( 'div', {'class' : 'five'} )
		app_histogram_five = app_five.find( 'span', {'class' : 'bar-number'} ).get_text().strip()
		histogram_five = app_histogram_five.replace(',','')
	except AttributeError as e:
		return None
	return int(histogram_five)

def histogram_four(soup):
	try:
		app_reviews = soup.find( 'div', {'class' : 'rating-histogram'} )
		app_four = app_reviews.find( 'div', {'class' : 'four'} )
		app_histogram_four = app_four.find( 'span', {'class' : 'bar-number'} ).get_text().strip()
		histogram_four = app_histogram_four.replace(',','')
	except AttributeError as e:
		return None
	return int(histogram_four)

def histogram_three(soup):
	try:
		app_reviews = soup.find( 'div', {'class' : 'rating-histogram'} )
		app_three = app_reviews.find( 'div', {'class' : 'three'} )
		app_histogram_three = app_three.find( 'span', {'class' : 'bar-number'} ).get_text().strip()
		histogram_three = app_histogram_three.replace(',','')
	except AttributeError as e:
		return None
	return int(histogram_three)

def histogram_two(soup):
	try:
		app_reviews = soup.find( 'div', {'class' : 'rating-histogram'} )
		app_two = app_reviews.find( 'div', {'class' : 'two'} )
		app_histogram_two = app_two.find( 'span', {'class' : 'bar-number'} ).get_text().strip()
		histogram_two = app_histogram_two.replace(',','')
	except AttributeError as e:
		return None
	return int(histogram_two)

def histogram_one(soup):
	try:
		app_reviews = soup.find( 'div', {'class' : 'rating-histogram'} )
		app_one = app_reviews.find( 'div', {'class' : 'one'} )
		app_histogram_one = app_one.find( 'span', {'class' : 'bar-number'} ).get_text().strip()
		histogram_one = app_histogram_one.replace(',','')
	except AttributeError as e:
		return None
	return int(histogram_one)
	
def screenshots(soup):
	AppScreenshots = []
	try:
		for app_screenshots in soup.find_all( 'img', {'class' : 'screenshot'} ):
			app_screenshot = app_screenshots.get('src').strip()
			AppScreenshots.append(app_screenshot)
	except AttributeError as e:
		return None
	return AppScreenshots
