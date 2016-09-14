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

"""Boto auth plugin for OAuth2.0 for Google Cloud Storage."""

from __future__ import absolute_import

from boto.auth_handler import AuthHandler
from boto.auth_handler import NotReadyToAuthenticate
from core.oauth.scriber_gcs_boto_plugin import plugin_utils

class ScriberAuthHandler(AuthHandler):

  capability = ['google-oauth2', 's3']

  def __init__(self, path, config, provider):
    self.oauth2_client = None
    if (provider.name == 'google'):
      self.oauth2_client = plugin_utils.OAuth2ClientFromBotoConfig(config)
    if not self.oauth2_client:
      raise NotReadyToAuthenticate()

  def add_auth(self, http_request):
    http_request.headers['Authorization'] = self.oauth2_client.GetAuthorizationHeader()
