# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Unit tests for the Yandex ID OAuth provider."""

from urllib.parse import parse_qs, urlparse
from unittest.mock import MagicMock, patch

import pytest
from django.test import Client, RequestFactory

from plane.authentication.adapter.error import (
    AUTHENTICATION_ERROR_CODES,
    AuthenticationException,
)
from plane.authentication.provider.oauth.yandex import YandexOAuthProvider
from plane.license.models import Instance

YANDEX_USERINFO = {
    "id": "1000034426",
    "login": "ivan.petrov",
    "client_id": "c1b2a3d4e5f60718293a4b5c6d7e8f90",
    "default_email": "ivan.petrov@yandex.ru",
    "emails": ["ivan.petrov@yandex.ru"],
    "real_name": "Иван Петров",
    "first_name": "Иван",
    "last_name": "Петров",
    "default_avatar_id": "31804/BswFT4RILtRnXoqhkzXkAOx8yI-1",
    "is_avatar_empty": False,
}


def _request():
    return RequestFactory().get("/auth/yandex/", HTTP_HOST="lokso.example")


def _configured_env():
    return patch.dict(
        "os.environ",
        {
            "YANDEX_CLIENT_ID": "test-client-id",
            "YANDEX_CLIENT_SECRET": "test-client-secret",
        },
    )


@pytest.mark.unit
class TestYandexProvider:
    @pytest.mark.django_db
    def test_not_configured_raises_meaningful_error(self):
        """Without client id/secret the provider must fail with YANDEX_NOT_CONFIGURED."""
        with patch.dict("os.environ", {}, clear=False):
            for key in ("YANDEX_CLIENT_ID", "YANDEX_CLIENT_SECRET"):
                import os

                os.environ.pop(key, None)
            with pytest.raises(AuthenticationException) as exc:
                YandexOAuthProvider(request=_request(), state="some-state")
        assert exc.value.error_code == AUTHENTICATION_ERROR_CODES["YANDEX_NOT_CONFIGURED"]
        assert exc.value.error_message == "YANDEX_NOT_CONFIGURED"

    @pytest.mark.django_db
    def test_auth_url_is_built_from_request_host(self):
        """The authorize url must point to oauth.yandex.ru and use a redirect_uri derived from the request host."""
        with _configured_env():
            provider = YandexOAuthProvider(request=_request(), state="state-123")
        parsed = urlparse(provider.get_auth_url())
        params = parse_qs(parsed.query)
        assert parsed.scheme == "https"
        assert parsed.netloc == "oauth.yandex.ru"
        assert parsed.path == "/authorize"
        assert params["response_type"] == ["code"]
        assert params["client_id"] == ["test-client-id"]
        assert params["state"] == ["state-123"]
        assert params["redirect_uri"] == ["http://lokso.example/auth/yandex/callback/"]

    @pytest.mark.django_db
    def test_token_and_userinfo_flow_with_mocked_responses(self):
        """Full token + userinfo exchange with mocked Yandex responses maps user data correctly."""
        token_response = MagicMock()
        token_response.json.return_value = {
            "access_token": "y0_test_access_token",
            "refresh_token": "y0_test_refresh_token",
            "token_type": "bearer",
            "expires_in": 31536000,
        }
        token_response.raise_for_status.return_value = None

        userinfo_response = MagicMock()
        userinfo_response.json.return_value = dict(YANDEX_USERINFO)
        userinfo_response.raise_for_status.return_value = None

        with _configured_env():
            provider = YandexOAuthProvider(request=_request(), code="auth-code")
            with (
                patch("plane.authentication.adapter.oauth.requests.post", return_value=token_response) as mock_post,
                patch(
                    "plane.authentication.provider.oauth.yandex.requests.get", return_value=userinfo_response
                ) as mock_get,
            ):
                provider.set_token_data()
                provider.set_user_data()

        # token request
        _, post_kwargs = mock_post.call_args
        assert mock_post.call_args[0][0] == "https://oauth.yandex.ru/token"
        assert post_kwargs["data"]["grant_type"] == "authorization_code"
        assert post_kwargs["data"]["code"] == "auth-code"
        assert post_kwargs["data"]["client_id"] == "test-client-id"
        assert post_kwargs["data"]["client_secret"] == "test-client-secret"

        # userinfo request must use the OAuth authorization scheme
        get_args, get_kwargs = mock_get.call_args
        assert get_args[0] == "https://login.yandex.ru/info?format=json"
        assert get_kwargs["headers"]["Authorization"] == "OAuth y0_test_access_token"

        # mapped user data
        assert provider.token_data["access_token"] == "y0_test_access_token"
        assert provider.user_data["email"] == "ivan.petrov@yandex.ru"
        user = provider.user_data["user"]
        assert user["provider_id"] == "1000034426"
        assert user["first_name"] == "Иван"
        assert user["last_name"] == "Петров"
        assert user["avatar"] == ("https://avatars.yandex.net/get-yapic/31804/BswFT4RILtRnXoqhkzXkAOx8yI-1/islands-200")
        assert user["is_password_autoset"] is True

    @pytest.mark.django_db
    def test_display_name_falls_back_to_login_when_no_real_name(self):
        userinfo = dict(YANDEX_USERINFO)
        userinfo.pop("first_name")
        userinfo.pop("real_name")
        userinfo["last_name"] = ""
        userinfo_response = MagicMock()
        userinfo_response.json.return_value = userinfo
        userinfo_response.raise_for_status.return_value = None

        with _configured_env():
            provider = YandexOAuthProvider(request=_request(), code="auth-code")
            provider.token_data = {"access_token": "tok"}
            with patch("plane.authentication.provider.oauth.yandex.requests.get", return_value=userinfo_response):
                provider.set_user_data()
        assert provider.user_data["user"]["first_name"] == "ivan.petrov"

    @pytest.mark.django_db
    def test_missing_email_fails_closed(self):
        userinfo = dict(YANDEX_USERINFO)
        userinfo["default_email"] = ""
        userinfo["emails"] = []
        userinfo_response = MagicMock()
        userinfo_response.json.return_value = userinfo
        userinfo_response.raise_for_status.return_value = None

        with _configured_env():
            provider = YandexOAuthProvider(request=_request(), code="auth-code")
            provider.token_data = {"access_token": "tok"}
            with patch("plane.authentication.provider.oauth.yandex.requests.get", return_value=userinfo_response):
                with pytest.raises(AuthenticationException) as exc:
                    provider.set_user_data()
        assert exc.value.error_code == AUTHENTICATION_ERROR_CODES["YANDEX_OAUTH_PROVIDER_ERROR"]


@pytest.mark.unit
class TestYandexEndpoints:
    @pytest.mark.django_db
    def test_initiate_without_instance_redirects_with_error(self):
        """GET /auth/yandex/ on a non-setup instance redirects back with INSTANCE_NOT_CONFIGURED."""
        response = Client().get("/auth/yandex/")
        assert response.status_code == 302
        assert f"error_code={AUTHENTICATION_ERROR_CODES['INSTANCE_NOT_CONFIGURED']}" in response["Location"]

    @pytest.mark.django_db
    def test_initiate_without_config_redirects_with_yandex_not_configured(self):
        """With a set-up instance but no Yandex credentials the initiate endpoint reports YANDEX_NOT_CONFIGURED."""
        import os

        from django.utils import timezone

        for key in ("YANDEX_CLIENT_ID", "YANDEX_CLIENT_SECRET"):
            os.environ.pop(key, None)
        Instance.objects.create(
            instance_name="Локсо",
            instance_id="test-instance-id",
            current_version="test",
            last_checked_at=timezone.now(),
            is_setup_done=True,
        )
        response = Client().get("/auth/yandex/")
        assert response.status_code == 302
        assert f"error_code={AUTHENTICATION_ERROR_CODES['YANDEX_NOT_CONFIGURED']}" in response["Location"]
