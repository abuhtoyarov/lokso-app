# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Unit tests for the LLM provider client factory and configuration.

Covers the Russian LLM presets added for the Lokso fork:
- YandexGPT: base url + gpt://<folder_id>/<model> resolution
- GigaChat: OAuth token exchange, Redis caching and Bearer wiring
Existing OpenAI behaviour is exercised as a regression guard.
"""

import time
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from plane.app.views.external.base import (
    GIGACHAT_OAUTH_URL,
    GIGACHAT_TOKEN_CACHE_KEY,
    GIGACHAT_TOKEN_MAX_TTL,
    LLMConfig,
    _resolve_yandex_model,
    build_llm_client,
    get_gigachat_access_token,
    get_llm_config,
)

BASE = "plane.app.views.external.base"


# The sandbox exports ALL_PROXY=socks5h://... which would make httpx demand the
# optional ``socksio`` package when the OpenAI client builds its default
# transport. Strip proxy env vars for this module so client construction is
# exercised without an outbound proxy (irrelevant to what we assert).
_PROXY_ENV_VARS = (
    "ALL_PROXY",
    "all_proxy",
    "HTTP_PROXY",
    "http_proxy",
    "HTTPS_PROXY",
    "https_proxy",
    "GRPC_PROXY",
    "grpc_proxy",
    "FTP_PROXY",
    "ftp_proxy",
)


@pytest.fixture(autouse=True)
def _strip_proxy_env(monkeypatch):
    for var in _PROXY_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def _yandex_env(**overrides):
    env = {
        "LLM_PROVIDER": "yandex",
        "LLM_API_KEY": "yandex-api-key",
        "LLM_FOLDER_ID": "b1gfolder",
        "LLM_MODEL": "",
    }
    env.update(overrides)
    return env


@pytest.mark.unit
class TestYandexModelResolution:
    def test_short_model_is_expanded_with_folder_and_latest(self):
        assert _resolve_yandex_model("yandexgpt", "b1g123") == "gpt://b1g123/yandexgpt/latest"

    def test_empty_model_defaults_to_yandexgpt_latest(self):
        assert _resolve_yandex_model("", "b1g123") == "gpt://b1g123/yandexgpt/latest"

    def test_model_with_version_is_kept(self):
        assert _resolve_yandex_model("yandexgpt-lite/rc", "b1g123") == "gpt://b1g123/yandexgpt-lite/rc"

    def test_full_uri_is_passed_through(self):
        uri = "gpt://other-folder/yandexgpt/latest"
        assert _resolve_yandex_model(uri, "b1g123") == uri

    def test_missing_folder_returns_none(self):
        assert _resolve_yandex_model("yandexgpt", None) is None


@pytest.mark.unit
class TestGetLLMConfig:
    @pytest.mark.django_db
    @override_settings(SKIP_ENV_VAR=False)
    def test_yandex_config_resolves_base_url_and_model(self):
        with patch.dict("os.environ", _yandex_env(), clear=False):
            config = get_llm_config()
        assert config is not None
        assert config.provider == "yandex"
        assert config.base_url == "https://llm.api.cloud.yandex.net/v1"
        assert config.model == "gpt://b1gfolder/yandexgpt/latest"
        assert config.folder_id == "b1gfolder"

    @pytest.mark.django_db
    @override_settings(SKIP_ENV_VAR=False)
    def test_yandex_without_folder_id_is_invalid(self):
        env = _yandex_env(LLM_FOLDER_ID="")
        with patch.dict("os.environ", env, clear=False):
            import os

            os.environ.pop("LLM_FOLDER_ID", None)
            config = get_llm_config()
        assert config is None

    @pytest.mark.django_db
    @override_settings(SKIP_ENV_VAR=False)
    def test_gigachat_config_defaults(self):
        env = {
            "LLM_PROVIDER": "gigachat",
            "LLM_API_KEY": "authkey",
            "LLM_MODEL": "GigaChat-Pro",
            "GIGACHAT_SCOPE": "GIGACHAT_API_CORP",
        }
        with patch.dict("os.environ", env, clear=False):
            config = get_llm_config()
        assert config is not None
        assert config.provider == "gigachat"
        assert config.base_url == "https://gigachat.devices.sberbank.ru/api/v1"
        assert config.model == "GigaChat-Pro"
        assert config.gigachat_scope == "GIGACHAT_API_CORP"

    @pytest.mark.django_db
    @override_settings(SKIP_ENV_VAR=False)
    def test_custom_requires_base_url(self):
        env = {
            "LLM_PROVIDER": "custom",
            "LLM_API_KEY": "k",
            "LLM_MODEL": "some-model",
            "LLM_BASE_URL": "",
        }
        with patch.dict("os.environ", env, clear=False):
            import os

            os.environ.pop("LLM_BASE_URL", None)
            config = get_llm_config()
        assert config is None

    @pytest.mark.django_db
    @override_settings(SKIP_ENV_VAR=False)
    def test_openai_still_validates_model(self):
        env = {
            "LLM_PROVIDER": "openai",
            "LLM_API_KEY": "sk-test",
            "LLM_MODEL": "not-a-real-model",
        }
        with patch.dict("os.environ", env, clear=False):
            config = get_llm_config()
        assert config is None

    @pytest.mark.django_db
    @override_settings(SKIP_ENV_VAR=False)
    def test_tls_verify_path_is_preserved(self):
        env = _yandex_env(LLM_TLS_VERIFY="/etc/ssl/certs/russian_trusted_root_ca.pem")
        with patch.dict("os.environ", env, clear=False):
            config = get_llm_config()
        assert config is not None
        assert config.tls_verify == "/etc/ssl/certs/russian_trusted_root_ca.pem"


@pytest.mark.unit
class TestBuildLLMClient:
    def test_yandex_client_uses_base_url_and_resolved_model(self):
        config = LLMConfig(
            api_key="yandex-key",
            model="gpt://b1gfolder/yandexgpt/latest",
            provider="yandex",
            base_url="https://llm.api.cloud.yandex.net/v1",
        )
        client, model = build_llm_client(config)
        assert "llm.api.cloud.yandex.net" in str(client.base_url)
        assert model == "gpt://b1gfolder/yandexgpt/latest"
        assert client.api_key == "yandex-key"

    def test_openai_client_without_base_url(self):
        config = LLMConfig(api_key="sk-test", model="gpt-4o-mini", provider="openai")
        client, model = build_llm_client(config)
        assert model == "gpt-4o-mini"
        assert client.api_key == "sk-test"

    def test_gigachat_client_performs_token_flow(self):
        config = LLMConfig(
            api_key="authorization-key",
            model="GigaChat",
            provider="gigachat",
            base_url="https://gigachat.devices.sberbank.ru/api/v1",
            gigachat_scope="GIGACHAT_API_PERS",
            tls_verify=True,
        )
        expires_at = int((time.time() + 30 * 60) * 1000)
        oauth_response = MagicMock()
        oauth_response.json.return_value = {"access_token": "access-token-123", "expires_at": expires_at}
        oauth_response.raise_for_status.return_value = None

        mock_ri = MagicMock()
        mock_ri.get.return_value = None

        with (
            patch(f"{BASE}.requests.post", return_value=oauth_response) as mock_post,
            patch(f"{BASE}.redis_instance", return_value=mock_ri),
        ):
            client, model = build_llm_client(config)

        # OpenAI client wired with the short-lived token as the Bearer credential
        assert client.api_key == "access-token-123"
        assert "gigachat.devices.sberbank.ru" in str(client.base_url)
        assert model == "GigaChat"

        # OAuth call shape
        assert mock_post.call_args.args[0] == GIGACHAT_OAUTH_URL
        headers = mock_post.call_args.kwargs["headers"]
        assert headers["Authorization"] == "Basic authorization-key"
        assert "RqUID" in headers
        assert mock_post.call_args.kwargs["data"] == {"scope": "GIGACHAT_API_PERS"}

        # Token cached with a TTL safely under the 30 minute lifetime
        mock_ri.set.assert_called_once()
        assert mock_ri.set.call_args.args[0] == GIGACHAT_TOKEN_CACHE_KEY
        assert 0 < mock_ri.set.call_args.kwargs["ex"] <= GIGACHAT_TOKEN_MAX_TTL

    def test_gigachat_uses_cached_token(self):
        mock_ri = MagicMock()
        mock_ri.get.return_value = b"cached-token"

        with (
            patch(f"{BASE}.requests.post") as mock_post,
            patch(f"{BASE}.redis_instance", return_value=mock_ri),
        ):
            token = get_gigachat_access_token("authorization-key", "GIGACHAT_API_PERS", True)

        assert token == "cached-token"
        mock_post.assert_not_called()
        mock_ri.set.assert_not_called()
