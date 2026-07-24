# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Unit tests for the VK ID OAuth provider."""

import base64
import hashlib
from urllib.parse import parse_qs, urlparse
from unittest.mock import MagicMock, patch

import pytest
from django.test import Client, RequestFactory

from plane.authentication.adapter.error import (
    AUTHENTICATION_ERROR_CODES,
    AuthenticationException,
)
from plane.authentication.provider.oauth.vk import VKOAuthProvider
from plane.license.models import Instance

VK_USERINFO = {
    "user": {
        "user_id": "1234567890",
        "first_name": "Иван",
        "last_name": "Петров",
        "avatar": "https://sun1-2.userapi.com/s/v1/ig2/avatar.jpg",
        "email": "ivan.petrov@vk.com",
        "sex": 2,
        "verified": False,
        "birthday": "01.01.2000",
    }
}


def _request():
    return RequestFactory().get("/auth/vk/", HTTP_HOST="lokso.example")


def _configured_env():
    return patch.dict("os.environ", {"VK_CLIENT_ID": "51234567"})


def _s256(verifier):
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")


@pytest.mark.unit
class TestVKProvider:
    @pytest.mark.django_db
    def test_not_configured_raises_meaningful_error(self):
        """Without a client id the provider must fail with VK_NOT_CONFIGURED."""
        with patch.dict("os.environ", {}, clear=False):
            import os

            for key in ("VK_CLIENT_ID", "VK_CLIENT_SECRET"):
                os.environ.pop(key, None)
            with pytest.raises(AuthenticationException) as exc:
                VKOAuthProvider(request=_request(), state="some-state")
        assert exc.value.error_code == AUTHENTICATION_ERROR_CODES["VK_NOT_CONFIGURED"]
        assert exc.value.error_message == "VK_NOT_CONFIGURED"

    @pytest.mark.django_db
    def test_auth_url_contains_pkce_challenge(self):
        """The authorize url must point to id.vk.com and carry an S256 PKCE challenge of the verifier."""
        with _configured_env():
            provider = VKOAuthProvider(request=_request(), state="state-123")
        parsed = urlparse(provider.get_auth_url())
        params = parse_qs(parsed.query)
        assert parsed.scheme == "https"
        assert parsed.netloc == "id.vk.com"
        assert parsed.path == "/authorize"
        assert params["response_type"] == ["code"]
        assert params["client_id"] == ["51234567"]
        assert params["state"] == ["state-123"]
        assert params["scope"] == ["email"]
        assert params["redirect_uri"] == ["http://lokso.example/auth/vk/callback/"]
        assert params["code_challenge_method"] == ["S256"]
        # the challenge must be the S256 transform of the stored verifier
        assert len(provider.code_verifier) >= 43
        assert params["code_challenge"] == [_s256(provider.code_verifier)]

    @pytest.mark.django_db
    def test_token_and_userinfo_flow_with_mocked_responses(self):
        """Full token + userinfo exchange with mocked VK ID responses maps user data correctly."""
        token_response = MagicMock()
        token_response.json.return_value = {
            "access_token": "vk1.a.test_access_token",
            "refresh_token": "vk1.a.test_refresh_token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "user_id": 1234567890,
            "state": "state-123",
            "scope": "email",
        }
        token_response.raise_for_status.return_value = None

        userinfo_response = MagicMock()
        userinfo_response.json.return_value = dict(VK_USERINFO)
        userinfo_response.raise_for_status.return_value = None

        with _configured_env():
            provider = VKOAuthProvider(
                request=_request(),
                code="auth-code",
                state="state-123",
                code_verifier="stored-code-verifier",
                device_id="device-id-from-callback",
            )

            # both the token and the userinfo endpoints are called via
            # requests.post, so dispatch the mocked responses by url
            def post_side_effect(url, *args, **kwargs):
                return token_response if url == "https://id.vk.com/oauth2/auth" else userinfo_response

            with patch("plane.authentication.adapter.oauth.requests.post", side_effect=post_side_effect) as mock_post:
                provider.set_token_data()
                provider.set_user_data()

        token_call, userinfo_call = mock_post.call_args_list

        # token request must carry the PKCE verifier and the callback device_id
        assert token_call[0][0] == "https://id.vk.com/oauth2/auth"
        token_data = token_call[1]["data"]
        assert token_data["grant_type"] == "authorization_code"
        assert token_data["code"] == "auth-code"
        assert token_data["code_verifier"] == "stored-code-verifier"
        assert token_data["device_id"] == "device-id-from-callback"
        assert token_data["client_id"] == "51234567"
        assert token_data["state"] == "state-123"
        assert token_data["redirect_uri"] == "http://lokso.example/auth/vk/callback/"

        # userinfo is a POST with the client id and the access token in the body
        assert userinfo_call[0][0] == "https://id.vk.com/oauth2/user_info"
        assert userinfo_call[1]["data"] == {
            "client_id": "51234567",
            "access_token": "vk1.a.test_access_token",
        }

        # mapped user data
        assert provider.token_data["access_token"] == "vk1.a.test_access_token"
        assert provider.user_data["email"] == "ivan.petrov@vk.com"
        user = provider.user_data["user"]
        assert user["provider_id"] == "1234567890"
        assert user["first_name"] == "Иван"
        assert user["last_name"] == "Петров"
        assert user["avatar"] == "https://sun1-2.userapi.com/s/v1/ig2/avatar.jpg"
        assert user["is_password_autoset"] is True

    @pytest.mark.django_db
    def test_token_response_without_access_token_fails(self):
        """VK ID may report errors in a 200 response body — a missing access token must fail."""
        token_response = MagicMock()
        token_response.json.return_value = {"error": "invalid_request", "error_description": "code_verifier mismatch"}
        token_response.raise_for_status.return_value = None

        with _configured_env():
            provider = VKOAuthProvider(
                request=_request(), code="auth-code", state="state-123", code_verifier="v", device_id="d"
            )
            with patch("plane.authentication.adapter.oauth.requests.post", return_value=token_response):
                with pytest.raises(AuthenticationException) as exc:
                    provider.set_token_data()
        assert exc.value.error_code == AUTHENTICATION_ERROR_CODES["VK_OAUTH_PROVIDER_ERROR"]

    @pytest.mark.django_db
    def test_missing_email_fails_closed(self):
        """VK может не вернуть email (не подтверждён / нет доступа) — вход должен завершиться ошибкой."""
        userinfo = {"user": dict(VK_USERINFO["user"])}
        userinfo["user"].pop("email")
        userinfo_response = MagicMock()
        userinfo_response.json.return_value = userinfo
        userinfo_response.raise_for_status.return_value = None

        with _configured_env():
            provider = VKOAuthProvider(request=_request(), code="auth-code", device_id="d", code_verifier="v")
            provider.token_data = {"access_token": "tok"}
            with patch("plane.authentication.provider.oauth.vk.requests.post", return_value=userinfo_response):
                with pytest.raises(AuthenticationException) as exc:
                    provider.set_user_data()
        assert exc.value.error_code == AUTHENTICATION_ERROR_CODES["VK_OAUTH_PROVIDER_ERROR"]
        assert "No email" in exc.value.error_message


@pytest.mark.unit
class TestVKEndpoints:
    @pytest.mark.django_db
    def test_initiate_without_instance_redirects_with_error(self):
        """GET /auth/vk/ on a non-setup instance redirects back with INSTANCE_NOT_CONFIGURED."""
        response = Client().get("/auth/vk/")
        assert response.status_code == 302
        assert f"error_code={AUTHENTICATION_ERROR_CODES['INSTANCE_NOT_CONFIGURED']}" in response["Location"]

    @pytest.mark.django_db
    def test_initiate_without_config_redirects_with_vk_not_configured(self):
        """With a set-up instance but no VK credentials the initiate endpoint reports VK_NOT_CONFIGURED."""
        import os

        from django.utils import timezone

        for key in ("VK_CLIENT_ID", "VK_CLIENT_SECRET"):
            os.environ.pop(key, None)
        Instance.objects.create(
            instance_name="Локсо",
            instance_id="test-instance-id",
            current_version="test",
            last_checked_at=timezone.now(),
            is_setup_done=True,
        )
        response = Client().get("/auth/vk/")
        assert response.status_code == 302
        assert f"error_code={AUTHENTICATION_ERROR_CODES['VK_NOT_CONFIGURED']}" in response["Location"]
