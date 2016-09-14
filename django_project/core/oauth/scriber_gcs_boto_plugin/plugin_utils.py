# Copyright 2014 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Helper routines to facilitate use of oauth2_client."""

from __future__ import absolute_import

import os

from core.oauth.constants import GOOGLE_OAUTH2_PROVIDER_AUTHORIZATION_URI, GOOGLE_OAUTH2_PROVIDER_TOKEN_URI, GOOGLE_OAUTH2_PROVIDER_TOKEN_URI, OOB_REDIRECT_URI
from core.gcs_oauth2_boto_plugin import oauth2_client
from oauth2client.client import OAuth2WebServerFlow

REFRESH_TOKEN = None
CLIENT_ID = None
CLIENT_SECRET = None

def OAuth2ClientFromBotoConfig(config,
    cred_type=oauth2_client.CredTypes.OAUTH2_USER_ACCOUNT):
  token_cache = None
  token_cache_type = config.get('OAuth2', 'token_cache', 'in_memory')
  if token_cache_type == 'file_system':
    if config.has_option('OAuth2', 'token_cache_path_pattern'):
      token_cache = oauth2_client.FileSystemTokenCache(
          path_pattern=config.get('OAuth2', 'token_cache_path_pattern'))
    else:
      token_cache = oauth2_client.FileSystemTokenCache()
  elif token_cache_type == 'in_memory':
    token_cache = oauth2_client.InMemoryTokenCache()
  else:
    raise Exception(
        "Invalid value for config option OAuth2/token_cache: %s" %
        token_cache_type)

  proxy_host = None
  proxy_port = None
  proxy_user = None
  proxy_pass = None
  if (config.has_option('Boto', 'proxy')
      and config.has_option('Boto', 'proxy_port')):
    proxy_host = config.get('Boto', 'proxy')
    proxy_port = int(config.get('Boto', 'proxy_port'))
    proxy_user = config.get('Boto', 'proxy_user', None)
    proxy_pass = config.get('Boto', 'proxy_pass', None)

  provider_authorization_uri = config.get(
      'OAuth2', 'provider_authorization_uri',
      GOOGLE_OAUTH2_PROVIDER_AUTHORIZATION_URI)
  provider_token_uri = config.get(
      'OAuth2', 'provider_token_uri', GOOGLE_OAUTH2_PROVIDER_TOKEN_URI)

  if cred_type == oauth2_client.CredTypes.OAUTH2_SERVICE_ACCOUNT:
    service_client_id = config.get('Credentials', 'gs_service_client_id', '')
    private_key_filename = config.get('Credentials', 'gs_service_key_file', '')
    key_file_pass = config.get('Credentials', 'gs_service_key_file_password',
                               GOOGLE_OAUTH2_DEFAULT_FILE_PASSWORD)
    with open(private_key_filename, 'rb') as private_key_file:
      private_key = private_key_file.read()

    return oauth2_client.OAuth2ServiceAccountClient(
        service_client_id, private_key, key_file_pass,
        access_token_cache=token_cache, auth_uri=provider_authorization_uri,
        token_uri=provider_token_uri,
        disable_ssl_certificate_validation=not(config.getbool(
            'Boto', 'https_validate_certificates', True)),
        proxy_host=proxy_host, proxy_port=proxy_port,
        proxy_user=proxy_user, proxy_pass=proxy_pass)

  elif cred_type == oauth2_client.CredTypes.OAUTH2_USER_ACCOUNT:
    client_id = CLIENT_ID if CLIENT_ID else config.get('OAuth2', 'client_id',
        os.environ.get('OAUTH2_CLIENT_ID', None))
    if not client_id:
      raise Exception(
          'client_id for your application obtained from '
          'https://console.developers.google.com must be set in a boto config '
          'or with OAUTH2_CLIENT_ID environment variable or with '
          'gcs_oauth2_boto_plugin.SetFallbackClientIdAndSecret function.')

    client_secret = CLIENT_SECRET if CLIENT_SECRET else config.get('OAuth2', 'client_secret',
        os.environ.get('OAUTH2_CLIENT_SECRET', None))
    if not client_secret:
      raise Exception(
          'client_secret for your application obtained from '
          'https://console.developers.google.com must be set in a boto config '
          'or with OAUTH2_CLIENT_SECRET environment variable or with '
          'gcs_oauth2_boto_plugin.SetFallbackClientIdAndSecret function.')

    refresh_token = REFRESH_TOKEN if REFRESH_TOKEN else config.get(
        'Credentials', 'gs_oauth2_refresh_token')
    return oauth2_client.OAuth2UserAccountClient(
        provider_token_uri, client_id, client_secret,
        refresh_token,
        auth_uri=provider_authorization_uri, access_token_cache=token_cache,
        disable_ssl_certificate_validation=not(config.getbool(
            'Boto', 'https_validate_certificates', True)),
        proxy_host=proxy_host, proxy_port=proxy_port,
        proxy_user=proxy_user, proxy_pass=proxy_pass,
        ca_certs_file=config.get_value('Boto', 'ca_certificates_file'))
  else:
    raise Exception('You have attempted to create an OAuth2 client without '
        'setting up OAuth2 credentials.')


def SetAuthInfo(refresh_token=None, client_id=None, client_secret=None):
  global REFRESH_TOKEN
  global CLIENT_ID
  global CLIENT_SECRET

  if refresh_token:
    REFRESH_TOKEN = refresh_token
  if client_id:
    CLIENT_ID = client_id
  if client_secret:
    CLIENT_SECRET = client_secret


def SetLock(lock):
  oauth2_client.token_exchange_lock = lock
