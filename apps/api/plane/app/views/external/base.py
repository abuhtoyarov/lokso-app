# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python import
import os
import uuid
from dataclasses import dataclass
from typing import List, Optional, Tuple, Union

# Third party import
import httpx
import requests
from openai import OpenAI

from rest_framework import status
from rest_framework.response import Response

# Module import
from plane.app.permissions import ROLE, allow_permission
from plane.app.serializers import ProjectLiteSerializer, WorkspaceLiteSerializer
from plane.db.models import Project, Workspace
from plane.license.utils.instance_value import get_configuration_value
from plane.settings.redis import redis_instance
from plane.utils.exception_logger import log_exception

from ..base import BaseAPIView


class LLMProvider:
    """Base class for LLM provider configurations"""

    name: str = ""
    models: List[str] = []
    default_model: str = ""
    # Default OpenAI-compatible base url. ``None`` means the OpenAI SDK default.
    default_base_url: Optional[str] = None
    # Whether ``LLM_MODEL`` must be one of ``models``. Providers that expose a
    # free-form / versioned model string (Yandex, GigaChat, custom endpoints)
    # set this to ``False``.
    validate_model: bool = True


class OpenAIProvider(LLMProvider):
    name = "OpenAI"
    models = ["gpt-3.5-turbo", "gpt-4o-mini", "gpt-4o", "o1-mini", "o1-preview"]
    default_model = "gpt-4o-mini"


class AnthropicProvider(LLMProvider):
    name = "Anthropic"
    models = [
        "claude-3-5-sonnet-20240620",
        "claude-3-haiku-20240307",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-2.1",
        "claude-2",
        "claude-instant-1.2",
        "claude-instant-1",
    ]
    default_model = "claude-3-sonnet-20240229"


class GeminiProvider(LLMProvider):
    name = "Gemini"
    models = ["gemini-pro", "gemini-1.5-pro-latest", "gemini-pro-vision"]
    default_model = "gemini-pro"


class YandexProvider(LLMProvider):
    """YandexGPT via the Yandex Cloud OpenAI-compatible endpoint.

    The model identifier has the form ``gpt://<folder_id>/<model>/<version>``
    (for example ``gpt://b1g.../yandexgpt/latest``). ``LLM_MODEL`` may hold the
    full URI or just the short model name (``yandexgpt``, ``yandexgpt-lite``,
    ``yandexgpt/rc`` ...) which is expanded using ``LLM_FOLDER_ID``.
    """

    name = "YandexGPT"
    models = []
    default_model = "yandexgpt/latest"
    default_base_url = "https://llm.api.cloud.yandex.net/v1"
    validate_model = False


class GigaChatProvider(LLMProvider):
    """GigaChat (Sber) via its OpenAI-compatible endpoint.

    Authentication is a two step flow: an "authorization key" (client
    credentials) is exchanged for a short lived (~30 min) access token at the
    NGW OAuth endpoint; that token is then sent as a Bearer credential to the
    chat completions endpoint. TLS to the Sber hosts is signed by the Russian
    Trusted Root CA (НУЦ Минцифры) which is usually not present in the default
    trust store -- point ``LLM_TLS_VERIFY`` at that CA bundle. Certificate
    source (do not vendor it into the repo):
    https://gu-st.ru/content/Other/doc/russian_trusted_root_ca.cer
    """

    name = "GigaChat"
    models = ["GigaChat", "GigaChat-Pro", "GigaChat-Max"]
    default_model = "GigaChat"
    default_base_url = "https://gigachat.devices.sberbank.ru/api/v1"
    validate_model = False


class CustomProvider(LLMProvider):
    """Any other OpenAI-compatible endpoint configured via ``LLM_BASE_URL``."""

    name = "Custom (OpenAI-compatible)"
    models = []
    default_model = ""
    default_base_url = None
    validate_model = False


SUPPORTED_PROVIDERS = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "gemini": GeminiProvider,
    "yandex": YandexProvider,
    "gigachat": GigaChatProvider,
    "custom": CustomProvider,
}

# GigaChat OAuth (client credentials -> access token) endpoint.
GIGACHAT_OAUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
# Cache key + safety margin (seconds) subtracted from the token lifetime so a
# cached token is never used right up to its expiry.
GIGACHAT_TOKEN_CACHE_KEY = "llm:gigachat:access_token"
GIGACHAT_TOKEN_SAFETY_MARGIN = 60
# Hard ceiling for the cache TTL. GigaChat tokens live ~30 min, keep well under.
GIGACHAT_TOKEN_MAX_TTL = 25 * 60


@dataclass
class LLMConfig:
    """Resolved LLM configuration for a single request."""

    api_key: str
    model: str
    provider: str
    base_url: Optional[str] = None
    folder_id: Optional[str] = None
    gigachat_scope: str = "GIGACHAT_API_PERS"
    # ``True`` (verify against system CAs), ``False`` (disable) or a path to a
    # CA bundle to use when talking to the provider over TLS.
    tls_verify: Union[bool, str] = True


def _parse_tls_verify(value: Optional[str]) -> Union[bool, str]:
    """Interpret the ``LLM_TLS_VERIFY`` config value.

    - empty / "1" / "true" / "yes" -> ``True`` (verify with the default trust store)
    - "0" / "false" / "no" -> ``False`` (disable verification, discouraged)
    - anything else -> treated as a filesystem path to a CA bundle / cert
    """
    if value is None:
        return True
    normalized = str(value).strip()
    if normalized == "" or normalized.lower() in ("1", "true", "yes", "on"):
        return True
    if normalized.lower() in ("0", "false", "no", "off"):
        return False
    return normalized


def _resolve_yandex_model(model: Optional[str], folder_id: Optional[str]) -> Optional[str]:
    """Build the ``gpt://<folder_id>/<model>/<version>`` identifier for YandexGPT."""
    model = (model or "").strip()
    # Already a fully qualified URI (gpt://... or ds://... for fine-tuned models)
    if "://" in model:
        return model
    base_model = model or YandexProvider.default_model
    # Default to the "latest" version when only the model family is given
    if "/" not in base_model:
        base_model = f"{base_model}/latest"
    if not folder_id:
        return None
    return f"gpt://{folder_id}/{base_model}"


def get_llm_config() -> Optional[LLMConfig]:
    """Read + validate the instance LLM configuration.

    Returns an :class:`LLMConfig` or ``None`` when the configuration is missing
    or invalid (the concrete reason is logged).
    """
    (
        api_key,
        provider_key,
        model,
        base_url,
        folder_id,
        gigachat_scope,
        tls_verify,
    ) = get_configuration_value(
        [
            {"key": "LLM_API_KEY", "default": os.environ.get("LLM_API_KEY", None)},
            {"key": "LLM_PROVIDER", "default": os.environ.get("LLM_PROVIDER", "openai")},
            {"key": "LLM_MODEL", "default": os.environ.get("LLM_MODEL", None)},
            {"key": "LLM_BASE_URL", "default": os.environ.get("LLM_BASE_URL", None)},
            {"key": "LLM_FOLDER_ID", "default": os.environ.get("LLM_FOLDER_ID", None)},
            {
                "key": "GIGACHAT_SCOPE",
                "default": os.environ.get("GIGACHAT_SCOPE", "GIGACHAT_API_PERS"),
            },
            {"key": "LLM_TLS_VERIFY", "default": os.environ.get("LLM_TLS_VERIFY", None)},
        ]
    )

    provider_key = (provider_key or "openai").lower()
    provider = SUPPORTED_PROVIDERS.get(provider_key)
    if not provider:
        log_exception(ValueError(f"Unsupported provider: {provider_key}"))
        return None

    if not api_key:
        log_exception(ValueError(f"Missing API key for provider: {provider.name}"))
        return None

    # Resolve the effective base url: explicit override wins, otherwise the
    # provider preset, otherwise the OpenAI SDK default (``None``).
    effective_base_url = (base_url or "").strip() or provider.default_base_url

    # Resolve the model per provider.
    resolved_model = (model or "").strip()
    if provider_key == "yandex":
        resolved_model = _resolve_yandex_model(model, (folder_id or "").strip() or None)
        if not resolved_model:
            log_exception(ValueError("YandexGPT requires LLM_FOLDER_ID (or a full gpt:// model URI) to be configured"))
            return None
    else:
        if not resolved_model:
            resolved_model = provider.default_model
        if provider.validate_model and resolved_model not in provider.models:
            log_exception(
                ValueError(
                    f"Model {resolved_model} not supported by {provider.name}. "
                    f"Supported models: {', '.join(provider.models)}"
                )
            )
            return None

    if provider_key == "custom" and not effective_base_url:
        log_exception(ValueError("Custom OpenAI-compatible provider requires LLM_BASE_URL to be configured"))
        return None

    return LLMConfig(
        api_key=api_key,
        model=resolved_model,
        provider=provider_key,
        base_url=effective_base_url,
        folder_id=(folder_id or "").strip() or None,
        gigachat_scope=(gigachat_scope or "GIGACHAT_API_PERS").strip(),
        tls_verify=_parse_tls_verify(tls_verify),
    )


def get_gigachat_access_token(
    authorization_key: str,
    scope: str,
    tls_verify: Union[bool, str] = True,
) -> str:
    """Return a (cached) GigaChat access token.

    Exchanges the client-credentials ``authorization_key`` for a bearer token at
    the NGW OAuth endpoint and caches it in Redis with a TTL safely below the
    token's ~30 minute lifetime. Subsequent calls reuse the cached token.
    """
    try:
        ri = redis_instance()
        cached = ri.get(GIGACHAT_TOKEN_CACHE_KEY)
        if cached:
            return cached.decode() if isinstance(cached, bytes) else str(cached)
    except Exception as e:
        # Redis is a best-effort cache here; never fail the request because of it.
        log_exception(e)
        ri = None

    response = requests.post(
        GIGACHAT_OAUTH_URL,
        headers={
            "Authorization": f"Basic {authorization_key}",
            "RqUID": str(uuid.uuid4()),
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        data={"scope": scope},
        verify=tls_verify,
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    token = payload.get("access_token")
    if not token:
        raise ValueError("GigaChat OAuth response did not contain an access_token")

    # ``expires_at`` is a unix timestamp in milliseconds.
    ttl = GIGACHAT_TOKEN_MAX_TTL
    expires_at = payload.get("expires_at")
    if expires_at:
        try:
            import time

            remaining = int(expires_at) / 1000 - time.time() - GIGACHAT_TOKEN_SAFETY_MARGIN
            if remaining > 0:
                ttl = min(GIGACHAT_TOKEN_MAX_TTL, int(remaining))
        except (TypeError, ValueError):
            ttl = GIGACHAT_TOKEN_MAX_TTL

    if ri is not None and ttl > 0:
        try:
            ri.set(GIGACHAT_TOKEN_CACHE_KEY, token, ex=ttl)
        except Exception as e:
            log_exception(e)

    return token


def build_llm_client(config: LLMConfig) -> Tuple[OpenAI, str]:
    """Build an OpenAI-compatible client and resolve the model for ``config``.

    This is the single factory used by all providers. For GigaChat it performs
    (and caches) the OAuth token exchange and wires up the CA bundle required
    for the Sber TLS chain.
    """
    provider_key = config.provider.lower()

    if provider_key == "gemini":
        # LiteLLM-style routing expects the provider prefix on the model.
        return OpenAI(api_key=config.api_key), f"gemini/{config.model}"

    if provider_key == "gigachat":
        token = get_gigachat_access_token(
            authorization_key=config.api_key,
            scope=config.gigachat_scope,
            tls_verify=config.tls_verify,
        )
        http_client = httpx.Client(verify=config.tls_verify)
        client = OpenAI(
            api_key=token,
            base_url=config.base_url or GigaChatProvider.default_base_url,
            http_client=http_client,
        )
        return client, config.model

    # OpenAI / Anthropic / Yandex / Custom -- plain OpenAI-compatible client.
    if config.base_url:
        client = OpenAI(api_key=config.api_key, base_url=config.base_url)
    else:
        client = OpenAI(api_key=config.api_key)
    return client, config.model


def get_llm_response(task: str, prompt: str, config: LLMConfig) -> Tuple[Optional[str], Optional[str]]:
    """Helper to get an LLM completion response."""
    final_text = task + "\n" + prompt
    provider_name = config.provider
    try:
        client, model = build_llm_client(config)
        chat_completion = client.chat.completions.create(
            model=model, messages=[{"role": "user", "content": final_text}]
        )
        text = chat_completion.choices[0].message.content
        return text, None
    except Exception as e:
        log_exception(e)
        error_type = e.__class__.__name__
        if error_type == "AuthenticationError":
            return None, f"Invalid API key for {provider_name}"
        elif error_type == "RateLimitError":
            return None, f"Rate limit exceeded for {provider_name}"
        else:
            return None, f"Error occurred while generating response from {provider_name}"


class GPTIntegrationEndpoint(BaseAPIView):
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def post(self, request, slug, project_id):
        config = get_llm_config()

        if not config:
            return Response(
                {"error": "LLM provider API key and model are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        task = request.data.get("task", False)
        if not task:
            return Response({"error": "Task is required"}, status=status.HTTP_400_BAD_REQUEST)

        text, error = get_llm_response(task, request.data.get("prompt", False), config)
        if not text and error:
            return Response(
                {"error": "An internal error has occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        workspace = Workspace.objects.get(slug=slug)
        project = Project.objects.get(pk=project_id)

        return Response(
            {
                "response": text,
                "response_html": text.replace("\n", "<br/>"),
                "project_detail": ProjectLiteSerializer(project).data,
                "workspace_detail": WorkspaceLiteSerializer(workspace).data,
            },
            status=status.HTTP_200_OK,
        )


class WorkspaceGPTIntegrationEndpoint(BaseAPIView):
    @allow_permission(allowed_roles=[ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def post(self, request, slug):
        config = get_llm_config()

        if not config:
            return Response(
                {"error": "LLM provider API key and model are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        task = request.data.get("task", False)
        if not task:
            return Response({"error": "Task is required"}, status=status.HTTP_400_BAD_REQUEST)

        text, error = get_llm_response(task, request.data.get("prompt", False), config)
        if not text and error:
            return Response(
                {"error": "An internal error has occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "response": text,
                "response_html": text.replace("\n", "<br/>"),
            },
            status=status.HTTP_200_OK,
        )


class UnsplashEndpoint(BaseAPIView):
    def get(self, request):
        (UNSPLASH_ACCESS_KEY,) = get_configuration_value(
            [
                {
                    "key": "UNSPLASH_ACCESS_KEY",
                    "default": os.environ.get("UNSPLASH_ACCESS_KEY"),
                }
            ]
        )
        # Check unsplash access key
        if not UNSPLASH_ACCESS_KEY:
            return Response([], status=status.HTTP_200_OK)

        # Query parameters
        query = request.GET.get("query", False)
        page = request.GET.get("page", 1)
        per_page = request.GET.get("per_page", 20)

        url = (
            f"https://api.unsplash.com/search/photos/?client_id={UNSPLASH_ACCESS_KEY}&query={query}&page=${page}&per_page={per_page}"
            if query
            else f"https://api.unsplash.com/photos/?client_id={UNSPLASH_ACCESS_KEY}&page={page}&per_page={per_page}"
        )

        headers = {"Content-Type": "application/json"}

        resp = requests.get(url=url, headers=headers)
        return Response(resp.json(), status=resp.status_code)
