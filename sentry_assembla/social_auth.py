"""
Obtain
ASSEMBLA_CLIENT_ID & ASSEMBLA_CLIENT_SECRET
and put into sentry.conf.py
"""
from __future__ import absolute_import

import base64
import logging
import requests

from social_auth.utils import setting
from social_auth.backends import BaseOAuth2, OAuthBackend
from social_auth.exceptions import AuthCanceled, AuthUnknownError

ASSEMBLA_TOKEN_EXCHANGE_URL = 'https://api.assembla.com/token'
ASSEMBLA_AUTHORIZATION_URL = 'https://api.assembla.com/authorization'
ASSEMBLA_USER_DETAILS_URL = 'https://api.assembla.com/v1/user.json'

logger = logging.getLogger('social_auth')

class AssemblaBackend(OAuthBackend):
    """Assembla OAuth authentication backend"""
    name = 'assembla'
    EXTRA_DATA = [
        ('email', 'email'),
        ('name', 'full_name'),
        ('id', 'id'),
        ('refresh_token', 'refresh_token')
    ]

    def get_user_details(self, response):
        """Return user details from Assembla account"""

        return {
            'email': response.get('email'),
            'id': response.get('id'),
            'full_name': response.get('name')
        }


class AssemblaAuth(BaseOAuth2):
    """Assembla OAuth authentication mechanism"""
    AUTHORIZATION_URL = ASSEMBLA_AUTHORIZATION_URL
    ACCESS_TOKEN_URL = ASSEMBLA_TOKEN_EXCHANGE_URL
    AUTH_BACKEND = AssemblaBackend
    SETTINGS_KEY_NAME = 'ASSEMBLA_CLIENT_ID'
    SETTINGS_SECRET_NAME = 'ASSEMBLA_CLIENT_SECRET'
    REDIRECT_STATE = False

    def user_data(self, access_token, *args, **kwargs):
        """Loads user data from service"""
        headers = {'Authorization': 'Bearer %s' % access_token}
        try:
            resp = requests.get(ASSEMBLA_USER_DETAILS_URL,
                                headers=headers)
            resp.raise_for_status()
            return resp.json()
        except ValueError:
            return None

    @classmethod
    def add_basic_auth_header(cls, headers):
        basic_auth = base64.encodestring('%s:%s' % (setting('ASSEMBLA_CLIENT_ID'), setting('ASSEMBLA_CLIENT_SECRET')))[:-1]
        headers.update({
            'Authorization': 'Basic %s' % basic_auth,
        })
        return headers
				
    def auth_complete(self, *args, **kwargs):
        """Completes login process, must return user instance"""
        self.process_error(self.data)
        params = self.auth_complete_params(self.validate_state())
        headers = self.add_basic_auth_header(self.auth_headers())
        try:
            response = requests.post(
                self.ACCESS_TOKEN_URL, 
                data=params,
                headers=headers
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if e.code == 400:
                raise AuthCanceled(self)
            else:
                raise
        else:
            try:
                response = response.json()
            except (ValueError, KeyError):
                raise AuthUnknownError(self)

        self.process_error(response)
        return self.do_auth(response['access_token'], response=response,
                            *args, **kwargs)

    @classmethod
    def refresh_token(cls, token, provider):
        params = cls.refresh_token_params(token, provider)
        headers = cls.add_basic_auth_header(cls.auth_headers())
        response = requests.post(
            cls.ACCESS_TOKEN_URL,
            data=params,
            headers=headers,
        )
        response.raise_for_status()
        logger.info('repsonse=%s', response.json())
        return response.json()

# Backend definition
BACKENDS = {
    'assembla': AssemblaAuth,
}
