# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import os
from datetime import datetime, timedelta
from urllib.parse import urlencode

import pytz
import requests

# Module imports
from plane.authentication.adapter.oauth import OauthAdapter
from plane.license.utils.instance_value import get_configuration_value
from plane.authentication.adapter.error import (
    AUTHENTICATION_ERROR_CODES,
    AuthenticationException,
)


class YandexOAuthProvider(OauthAdapter):
    token_url = "https://oauth.yandex.ru/token"
    userinfo_url = "https://login.yandex.ru/info?format=json"
    scope = "login:email login:info login:avatar"
    provider = "yandex"

    def __init__(self, request, code=None, state=None, callback=None):
        (YANDEX_CLIENT_ID, YANDEX_CLIENT_SECRET) = get_configuration_value(
            [
                {
                    "key": "YANDEX_CLIENT_ID",
                    "default": os.environ.get("YANDEX_CLIENT_ID"),
                },
                {
                    "key": "YANDEX_CLIENT_SECRET",
                    "default": os.environ.get("YANDEX_CLIENT_SECRET"),
                },
            ]
        )

        if not (YANDEX_CLIENT_ID and YANDEX_CLIENT_SECRET):
            raise AuthenticationException(
                error_code=AUTHENTICATION_ERROR_CODES["YANDEX_NOT_CONFIGURED"],
                error_message="YANDEX_NOT_CONFIGURED",
            )

        client_id = YANDEX_CLIENT_ID
        client_secret = YANDEX_CLIENT_SECRET

        redirect_uri = f"""{"https" if request.is_secure() else "http"}://{request.get_host()}/auth/yandex/callback/"""
        url_params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": state,
        }
        auth_url = f"https://oauth.yandex.ru/authorize?{urlencode(url_params)}"

        super().__init__(
            request,
            self.provider,
            client_id,
            self.scope,
            redirect_uri,
            auth_url,
            self.token_url,
            self.userinfo_url,
            client_secret,
            code,
            callback=callback,
        )

    def set_token_data(self):
        data = {
            "code": self.code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "authorization_code",
        }
        token_response = self.get_user_token(data=data)
        super().set_token_data(
            {
                "access_token": token_response.get("access_token"),
                "refresh_token": token_response.get("refresh_token", None),
                "access_token_expired_at": (
                    datetime.now(tz=pytz.utc) + timedelta(seconds=token_response.get("expires_in"))
                    if token_response.get("expires_in")
                    else None
                ),
                "refresh_token_expired_at": None,
                "id_token": token_response.get("id_token", ""),
            }
        )

    def get_user_response(self):
        # Yandex requires the "OAuth" authorization scheme instead of "Bearer"
        try:
            headers = {"Authorization": f"OAuth {self.token_data.get('access_token')}"}
            response = requests.get(self.get_user_info_url(), headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            self.logger.warning("Error getting user response from Yandex")
            raise AuthenticationException(
                error_code=AUTHENTICATION_ERROR_CODES["YANDEX_OAUTH_PROVIDER_ERROR"],
                error_message="YANDEX_OAUTH_PROVIDER_ERROR",
            )

    def set_user_data(self):
        user_info_response = self.get_user_response()
        # Yandex Passport guarantees that default_email is a confirmed address of
        # the account, so it is safe to use for the login/sign-up flow. If the
        # user has not granted the login:email scope (or has no email), fail
        # closed instead of trusting any other field.
        email = user_info_response.get("default_email")
        if not email:
            emails = user_info_response.get("emails") or []
            email = emails[0] if emails else None
        if not email:
            raise AuthenticationException(
                error_code=AUTHENTICATION_ERROR_CODES["YANDEX_OAUTH_PROVIDER_ERROR"],
                error_message="YANDEX_OAUTH_PROVIDER_ERROR: No email found",
            )

        # Build the avatar url from the default avatar id if the user has one
        avatar = None
        if not user_info_response.get("is_avatar_empty", True) and user_info_response.get("default_avatar_id"):
            avatar = f"https://avatars.yandex.net/get-yapic/{user_info_response.get('default_avatar_id')}/islands-200"

        first_name = (
            user_info_response.get("first_name")
            or user_info_response.get("real_name")
            or user_info_response.get("login")
        )

        super().set_user_data(
            {
                "email": email,
                "user": {
                    "provider_id": str(user_info_response.get("id")),
                    "email": email,
                    "avatar": avatar,
                    "first_name": first_name,
                    "last_name": user_info_response.get("last_name") or "",
                    "is_password_autoset": True,
                },
            }
        )
