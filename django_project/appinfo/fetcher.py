import logging
import requests
import urllib2
import simplejson
from appinfo.constants import ANDROID_PLATFORM_STRING, IOS_PLATFORM_STRING
from appinfo.models import AppInfo, AppScreenshot, PlatformType
from core.currency import convert_decimal_to_usd, symbol_to_currency_code
from core.db.constants import TEN_PLACES
from datetime import datetime, timedelta
from dateutil import parser
from decimal import Decimal
from django.conf import settings
from django.db import transaction
from pytz import utc
from re import match
from scriber.api import Scriber
from dashboard import google_crawlplay

logger = logging.getLogger(__name__)

_ANDROID_APP_INFO_API_KEY = '1aad42af66eb5c148d29e72adb932dc2'
#_ANDROID_APP_INFO_URL = 'http://api.playstoreapi.com/v1.1/apps/%s?key=%s'
_ANDROID_APP_INFO_URL = 'http://mobbo.com/Android/AppDetails/%s'
_IOS_BUNDLE_ID_INFO_URL = 'https://itunes.apple.com/lookup?bundleId=%s'
_IOS_ID_INFO_URL = 'https://itunes.apple.com/lookup?id=%s'

_FILE_SIZE_MULTIPLIER = {
    'k': 1000,
    'm': 1000000,
    'g': 1000000000,
}

_STALE_INFO_DELTA = timedelta(days=1)


# TODO(d-felix): This functionality is out of place here.
# Consider merging the appinfo and appstore django apps.
def _update_primary_category(appInfo):
  if appInfo.platform == IOS_PLATFORM_STRING:
    trackId = long(appInfo.identifier) if appInfo.identifier is not None else None
    api.update_primary_category_ios(bundle_id=appInfo.app, track_id=trackId,
                                    ios_genre_id=appInfo.ios_genre_id, name=appInfo.name)
  elif appInfo.platform == ANDROID_PLATFORM_STRING:
    logger.info('Primary category updates not yet implemented for Android apps')
    pass
  else:
    raise ValueError('Unrecognized platform %s' % appInfo.platform)


class AbstractAppInfoFetcher():

  """
  An abstract base class for app information fetchers.
  Subclasses are expected to override the fetch_direct method.
  """

  def __init__(self, platform):
    self.platform = platform

  def retrieve_from_db(self, app_str):
    stale_info_threshold = datetime.now().replace(tzinfo=utc) - _STALE_INFO_DELTA
    try:
      appInfo = AppInfo.objects.filter(app=app_str, platform=self.platform, fetch_time__gte=stale_info_threshold).latest('fetch_time')
      return appInfo
    except AppInfo.DoesNotExist:
      return None

  def fetch(self, app_str, sku, customerId, login_info_id, direct=False):
    appInfo = None
    if not direct:
      appInfo = self.retrieve_from_db(app_str)
    if appInfo is None:
      appInfo = self.fetch_direct(app_str, sku, customerId, login_info_id)
      # appInfo shouldn't be None at this point.
      # TODO(d-felix): Debug this.
      if appInfo is not None:
        if not settings.DEBUG:
          _update_primary_category(appInfo)
    return appInfo

  def fetch_direct(self, app_str, sku, customerId, login_info_id):
    raise NotImplementedError('Implementation not defined for abstract base class.')


# Fetcher sets or updates AppStoreApp and Artist data from the iTunes API
class AppStoreFetcher():

  # itunes denies requests with more than 10 sometimes
  def updateAppStoreApps(self, app_store_apps):
    if len(app_store_apps) > 150:
      return

    app_id_csv = "0"
    for app in app_store_apps:
      app_id_csv += "," + str(app.track_id)

    url = _IOS_ID_INFO_URL % app_id_csv

    response = requests.get(url, timeout=60)

    itunes_app_array_json = response.json()['results']
    artist_id_array = []

    # bulk fetch artists. Create missing artists
    for app_json in itunes_app_array_json:
      artist_id_array.append(app_json['artistId'])

    app_store_artists = list(AppStoreArtist.objects.filter(artist_id__in=artist_id_array))
    app_store_artist_dict = {x.artist_id: x for x in app_store_artists}

    with transaction.atomic():
      for app_json in itunes_app_array_json:
        app_track_id = app_json['trackId']
        app_is_free = app_json['price'] == 0 or app_json['formattedPrice'] == 'Free'
        app_store_app = [x for x in app_store_apps if x.track_id == app_track_id][0]
        app_store_app.name = app_json['trackName']

        if not app_store_app.primary_category:
          app_store_category = AppStoreCategory.objects.filter(
              ios_genre_id=app_json['primaryGenreId'])[0]
          app_store_app.primary_category = app_store_category

        artist_id = app_json['artistId']
        app_store_artist = None

        if artist_id in app_store_artist_dict:
          app_store_artist = app_store_artist_dict[artist_id]

        if not app_store_artist:
          app_store_artist, created = AppStoreArtist.objects.get_or_create(
              artist_id=artist_id, defaults={
                  'name': app_json['artistName'], 'platform': app_store_app.platform})
          if created:
            app_store_artist_dict[artist_id] = app_store_artist
        app_store_app.artist = app_store_artist
        app_store_app.is_free = app_is_free
        app_store_app.save()


def parseItunesAppJson(appJson, customerId, login_info_id, sku):
  price = appJson['price']
  currency = appJson['currency']
  amtLocalRaw = Decimal(str(price))
  amtLocal = amtLocalRaw.quantize(TEN_PLACES)
  amtLocalMicros = long(amtLocalRaw * 1000000)
  amtUsd = convert_decimal_to_usd(amtLocalRaw, currency)
  amtUsdMicros = long(amtUsd * 1000000) if amtUsd is not None else None
  if amtUsd is None:
    logger.info("Currency conversion failed due to unrecognized currency: %s" % currency)

  releaseDate = parser.parse(appJson['releaseDate'])
  platformType = PlatformType.objects.get(pk=1)
	
  appInfo = AppInfo(
      app=appJson['bundleId'],
      sku=sku,
      price=amtUsdMicros,
      customer_id = customerId,
      customer_account_id = login_info_id,
      platform_type_id=platformType,
      category=appJson['primaryGenreName'],
      currency=currency,
      developer=appJson['sellerName'],
      size=appJson['fileSizeBytes'],
      icon_url=appJson['artworkUrl60'],
      identifier=str(appJson['trackId']),
      name=appJson['trackName'],
      platform=IOS_PLATFORM_STRING,
      release_date=releaseDate,
      version=appJson['version'],
      formatted_price=appJson['formattedPrice'],
      description=appJson['description'],
      artist_id=appJson['artistId'],
      content_rating=appJson['contentAdvisoryRating'],
      rating=appJson['contentAdvisoryRating']
  )

  return appInfo


class ItunesBundleIdLookupAppInfoFetcher(AbstractAppInfoFetcher):

  def fetch_direct(self, app_str,customerId, login_info_id):
    if not app_str:
      return None

    url = _IOS_BUNDLE_ID_INFO_URL % app_str
    response = requests.get(url)

    # Retrieve the first entry of the results list.
    results = response.json().get('results', [{}])
    if not results or len(results) == 0:
      return None
    results = results[0]

    appInfo = parseItunesAppJson(results, customerId, login_info_id)
    appInfo.save()
    return appInfo


class ItunesIdLookupAppInfoFetcher(AbstractAppInfoFetcher):

  def retrieve_from_db(self, apple_identifier):
    stale_info_threshold = datetime.now().replace(tzinfo=utc) - _STALE_INFO_DELTA
    try:
      identifierStr = str(apple_identifier)
      appInfo = AppInfo.objects.filter(identifier=identifierStr, platform=self.platform,
                                       fetch_time__gte=stale_info_threshold).latest('fetch_time')
      return appInfo
    except AppInfo.DoesNotExist:
      return None

  def fetch_direct(self, apple_identifier, sku, customerId, login_info_id):
    if not apple_identifier:
      return None

    identifierStr = str(apple_identifier)
    url = _IOS_ID_INFO_URL % identifierStr
    response = requests.get(url)

    # Retrieve the first entry of the results list.
    resultsList = response.json().get('results', [{}])
    if not resultsList:
      return None
    results = resultsList[0]
    
    appInfo = parseItunesAppJson(results, customerId, login_info_id, sku)
    app_screenshots = results['screenshotUrls']
    with transaction.atomic():
        appInfo.save()
        for record in app_screenshots:
            appScreenshot = AppScreenshot(screenshots=record,app_info_id=appInfo)
            appScreenshot.save()
    #appInfo.save()
    return appInfo


class PlaystoreapiAppInfoFetcher(AbstractAppInfoFetcher):

  def fetch_direct(self, app_str, sku, customerId, login_info_id):
    return self.fetch_direct_with_api_key(app_str, sku, customerId, login_info_id, _ANDROID_APP_INFO_API_KEY)

  def fetch_direct_with_api_key(self, app_str, sku, customerId, login_info_id, api_key):
    if not app_str:
      return None
    
    #results = google_crawlplay.get_app_detail(app_str)
    url = _ANDROID_APP_INFO_URL % (app_str)
    hdr = {'User-Agent':'Mozilla/5.0'}
    req = urllib2.Request(url,headers=hdr)
    try:
        response = urllib2.urlopen(req)
        results = simplejson.load(response)
        if results['name'] is not None:
            #platformType = PlatformType.objects.filter(platform_type_str='Android')
            datestr = str(results['updatedTo'])
            dt = parser.parse(datestr).date()
            platformType = PlatformType.objects.get(pk=2)
            app_screenshots = results['screenshots'].split(",")
            appInfo = AppInfo(app=app_str,
                customer_id = customerId,
                customer_account_id = login_info_id,
                name=results['name'],
                platform=ANDROID_PLATFORM_STRING,
                platform_type_id=platformType,
                category=results['category'],
                price=results['price'],
                currency='USD',
                icon_url=results['icon'][:-3],
                rating=results['rating'],
                rating1=results['rating1'],
                rating2=results['rating2'],
                rating3=results['rating3'],
                rating4=results['rating4'],
                rating5=results['rating5'],
                version=results['version'],
                content_rating=results['contentRating'],
                size=results['size'],
                developer_email=results['email'],
                developer_website=results['website'],
                install=results['installs'],
                has_iap=results['hasIAP'],
                iap_min=results['IAPmin'],
                iap_max=results['IAPmax'],
                release_date = dt
            )
            with transaction.atomic():
                appInfo.save()
                for record in app_screenshots:
                    appScreenshot = AppScreenshot(screenshots=record[:-3],app_info_id=appInfo)
                    appScreenshot.save()
            return
        else:
            return None
    except urllib2.HTTPError, e:
        logger.info('Google play app %s information not found mobbo.com' %
            (app_str))
        pass

# Module scope fetchers
IOS_BUNDLE_ID_APP_INFO_FETCHER = ItunesBundleIdLookupAppInfoFetcher(IOS_PLATFORM_STRING)
IOS_ID_APP_INFO_FETCHER = ItunesIdLookupAppInfoFetcher(IOS_PLATFORM_STRING)
ANDROID_APP_INFO_FETCHER = PlaystoreapiAppInfoFetcher(ANDROID_PLATFORM_STRING)

# We use bundle ID as the default iOS identifier.
PLATFORM_TYPE_TO_FETCHER_MAP = {
    IOS_BUNDLE_ID_APP_INFO_FETCHER.platform: IOS_BUNDLE_ID_APP_INFO_FETCHER,
    ANDROID_APP_INFO_FETCHER.platform: ANDROID_APP_INFO_FETCHER,
}


def fetcher_for_platform_type(platform_type_str):
  """
  Returns the proper app info fetcher instance for the provided platform type
  string descriptor. None is returned for unrecognized platforms.
  """
  return PLATFORM_TYPE_TO_FETCHER_MAP.get(platform_type_str, None)


def fetch(app_str, platform_type_str, direct=False):
  """
  A convenience function for fetching app info for the provided app identifier
  and platform type. The app identifier is expected to be the bundle ID for
  iOS apps, and the package ID for Android apps.
  """
  fetcher = fetcher_for_platform_type(platform_type_str)
  if fetcher is None:
    return None
  return fetcher.fetch(app_str, direct)
