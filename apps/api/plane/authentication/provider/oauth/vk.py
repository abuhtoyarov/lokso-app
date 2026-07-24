# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import base64
import hashlib
import os
import secrets
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


class VKOAuthProvider(OauthAdapter):
    """VK ID OAuth 2.1 provider (id.vk.com) with the mandatory PKCE flow."""

    token_url = "https://id.vk.com/oauth2/auth"
    userinfo_url = "https://id.vk.com/oauth2/user_info"
    scope = "email"
    provider = "vk"

    def __init__(self, request, code=None, state=None, callback=None, code_verifier=None, device_id=None):
        (VK_CLIENT_ID, VK_CLIENT_SECRET) = get_configuration_value(
            [
                {
                    "key": "VK_CLIENT_ID",
                    "default": os.environ.get("VK_CLIENT_ID"),
                },
                {
                    "key": "VK_CLIENT_SECRET",
                    "default": os.environ.get("VK_CLIENT_SECRET"),
                },
            ]
        )

        # VK ID exchanges the code with PKCE only, so the client secret is not
        # required for the token request — only the app id (client id) is.
        if not VK_CLIENT_ID:
            raise AuthenticationException(
                error_code=AUTHENTICATION_ERROR_CODES["VK_NOT_CONFIGURED"],
                error_message="VK_NOT_CONFIGURED",
            )

        client_id = VK_CLIENT_ID
        client_secret = VK_CLIENT_SECRET

        self.state = state
        # device_id is returned by VK ID alongside the code and is mandatory
        # in the token request.
        self.device_id = device_id
        # PKCE: the verifier is generated on the authorize step, persisted in
        # the session by the initiate view and passed back on the callback.
        self.code_verifier = code_verifier or secrets.token_urlsafe(64)
        code_challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(self.code_verifier.encode("ascii")).digest())
            .rstrip(b"=")
            .decode("ascii")
        )

        redirect_uri = f"""{"https" if request.is_secure() else "http"}://{request.get_host()}/auth/vk/callback/"""
        url_params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "scope": self.scope,
        }
        auth_url = f"https://id.vk.com/authorize?{urlencode(url_params)}"

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
            "grant_type": "authorization_code",
            "code": self.code,
            "code_verifier": self.code_verifier,
            "client_id": self.client_id,
            "device_id": self.device_id,
            "redirect_uri": self.redirect_uri,
            "state": self.state,
        }
        token_response = self.get_user_token(data=data)
        # VK ID reports some errors with a 200 response and an "error" payload,
        # so the missing access token has to be treated as a failure explicitly.
        if not token_response.get("access_token"):
            self.logger.warning("Error getting access token from VK ID")
            raise AuthenticationException(
                error_code=AUTHENTICATION_ERROR_CODES["VK_OAUTH_PROVIDER_ERROR"],
                error_message="VK_OAUTH_PROVIDER_ERROR",
            )
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
        # VK ID serves user info via a POST request with the client id and the
        # access token in the form body instead of an Authorization header.
        try:
            data = {
                "client_id": self.client_id,
                "access_token": self.token_data.get("access_token"),
            }
            response = requests.post(self.get_user_info_url(), data=data)
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            self.logger.warning("Error getting user response from VK ID")
            raise AuthenticationException(
                error_code=AUTHENTICATION_ERROR_CODES["VK_OAUTH_PROVIDER_ERROR"],
                error_message="VK_OAUTH_PROVIDER_ERROR",
            )

    def set_user_data(self):
        user_info_response = self.get_user_response()
        user_info = user_info_response.get("user") or {}

        # VK ID returns the email only when the user has a confirmed address
        # and has granted the email scope. Without an email the account cannot
        # be matched safely, so fail closed with a meaningful error.
        email = user_info.get("email")
        if not email:
            raise AuthenticationException(
                error_code=AUTHENTICATION_ERROR_CODES["VK_OAUTH_PROVIDER_ERROR"],
                error_message="VK_OAUTH_PROVIDER_ERROR: No email found",
            )

        first_name = user_info.get("first_name") or email.split("@")[0]

        super().set_user_data(
            {
                "email": email,
                "user": {
                    "provider_id": str(user_info.get("user_id")),
                    "email": email,
                    "avatar": user_info.get("avatar"),
                    "first_name": first_name,
                    "last_name": user_info.get("last_name") or "",
                    "is_password_autoset": True,
                },
            }
        )
