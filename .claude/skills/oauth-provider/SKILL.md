---
name: oauth-provider
description: Use when adding a new OAuth or OpenID sign-in provider to Lokso (for example Sber ID or T-Bank ID) — walks every backend and frontend touchpoint the existing Yandex ID and VK ID providers occupy, so none is missed, and covers the instance-config keys, admin form and unit tests.
user_invocable: true
---

# Adding an OAuth Provider

Add a new sign-in provider end to end. The reference implementations are `yandex.py` and `vk.py`; read both before starting — VK ID uses PKCE, Yandex ID does not, and the new provider will resemble one of them.

## Before you start

Client ID and client secret come from the provider's own console and are Artyom's to obtain — ask for them, never invent placeholder credentials. The redirect URI follows the existing shape: `http://localhost:8000/auth/<provider>/callback/` locally.

## Backend touchpoints

Work through all of these — a provider that is only half-registered fails at runtime in a way that is hard to trace:

| File                                                               | What to add                                                                                                                                                                                                                                                                                  |
| ------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `apps/api/plane/authentication/provider/oauth/<provider>.py`       | The provider class itself — authorize URL, token exchange, userinfo mapping, raises `AuthenticationException` using the error codes below                                                                                                                                                    |
| `apps/api/plane/authentication/views/app/<provider>.py`            | Initiate and callback views for the main app                                                                                                                                                                                                                                                 |
| `apps/api/plane/authentication/views/space/<provider>.py`          | Initiate and callback views for the public space                                                                                                                                                                                                                                             |
| `apps/api/plane/authentication/views/__init__.py`                  | Export the new app and space views                                                                                                                                                                                                                                                           |
| `apps/api/plane/authentication/urls.py`                            | Route `auth/<provider>/` and `auth/<provider>/callback/`, plus the `spaces/<provider>/` and `spaces/<provider>/callback/` pair                                                                                                                                                               |
| `apps/api/plane/authentication/adapter/error.py`                   | Add `<PROVIDER>_NOT_CONFIGURED` and `<PROVIDER>_OAUTH_PROVIDER_ERROR` to `AUTHENTICATION_ERROR_CODES` with new numeric codes                                                                                                                                                                 |
| `apps/api/plane/authentication/adapter/oauth.py`                   | Add an `elif self.provider == "<provider>":` branch in `authentication_error_code()` returning `"<PROVIDER>_OAUTH_PROVIDER_ERROR"` — miss this and failures report as generic `OAUTH_NOT_CONFIGURED`                                                                                         |
| `apps/api/plane/authentication/adapter/base.py`                    | Add `"<provider>": "ENABLE_<PROVIDER>_SYNC"` to the `provider_config_map` in `check_sync_enabled()`                                                                                                                                                                                          |
| `apps/api/plane/license/api/views/instance.py`                     | Fetch `IS_<PROVIDER>_ENABLED` via `get_configuration_value` and expose it as `is_<provider>_enabled` in the instance payload                                                                                                                                                                 |
| `apps/api/plane/license/management/commands/configure_instance.py` | Add `IS_<PROVIDER>_ENABLED` to the `keys` list, and a matching `if key == "IS_<PROVIDER>_ENABLED":` block that reads the provider's client id (and secret, if the provider doesn't use PKCE) and creates the `InstanceConfiguration` row — this is what actually turns the sign-in button on |
| `apps/api/plane/utils/instance_config_variables/core.py`           | Add a `<provider>_config_variables` list bootstrapping `<PROVIDER>_CLIENT_ID`, `<PROVIDER>_CLIENT_SECRET` (encrypted) and `ENABLE_<PROVIDER>_SYNC`, and splice it into the aggregate list                                                                                                    |

Config keys are not all one naming scheme — there are three separate things, each bootstrapped in a different place:

- `<PROVIDER>_CLIENT_ID` / `<PROVIDER>_CLIENT_SECRET` — bootstrapped in `utils/instance_config_variables/core.py`, edited from the admin form
- `ENABLE_<PROVIDER>_SYNC` — also bootstrapped in `utils/instance_config_variables/core.py`, read by `adapter/base.py`'s `check_sync_enabled()`
- `IS_<PROVIDER>_ENABLED` — bootstrapped separately by `configure_instance.py` (not by the static list above, because its value is derived from whether client id/secret are present), read by `license/api/views/instance.py` and exposed to the frontend as `is_<provider>_enabled`

`configure_instance.py` runs on every container start (see `bin/docker-entrypoint-api.sh` and `bin/docker-entrypoint-api-local.sh`). The admin panel's PATCH endpoint only updates existing `InstanceConfiguration` rows — it cannot create the `IS_<PROVIDER>_ENABLED` row. So without a matching block in `configure_instance.py`, entering valid credentials in the admin panel can never turn the sign-in button on.

Fail closed: if the provider returns no email, reject the sign-in rather than fabricating one. Both `yandex.py` and `vk.py` do this — follow them.

## Frontend touchpoints

| File                                                                  | What to add                                               |
| --------------------------------------------------------------------- | --------------------------------------------------------- |
| `packages/types/src/instance/auth.ts`                                 | The provider's config keys in the auth configuration type |
| `packages/types/src/instance/base.ts`                                 | The provider's enabled flag                               |
| `packages/constants/src/auth/core.ts`                                 | The provider constant                                     |
| `apps/admin/app/(all)/(dashboard)/authentication/<provider>/page.tsx` | Admin settings page                                       |
| `apps/admin/app/(all)/(dashboard)/authentication/<provider>/form.tsx` | Client ID / secret form                                   |
| `apps/admin/components/authentication/<provider>-config.tsx`          | The provider's row on the authentication list             |
| `apps/admin/app/routes.ts`                                            | Route for the settings page                               |
| `apps/admin/components/common/header/core.ts`                         | Breadcrumb entry                                          |
| `apps/admin/hooks/oauth/core.tsx`                                     | Admin-side OAuth hook                                     |
| `apps/web/core/hooks/oauth/core.tsx`                                  | Sign-in button and redirect on the web app                |

Strings go through `packages/i18n/src/locales` — see the `translate` skill. Do not hardcode user-facing text.

## Tests

Mirror `apps/api/plane/tests/unit/authentication/test_yandex_provider.py` and `test_vk_provider.py`. Cover at minimum:

- provider not configured → the provider's `NOT_CONFIGURED` error code
- the authorize URL carries the expected parameters (and, for a PKCE provider, an S256 challenge derived from the stored verifier)
- a mocked token and userinfo exchange maps id, name, avatar and email correctly
- a token response with no access token → the provider's `OAUTH_PROVIDER_ERROR`
- a userinfo response with no email fails closed
- the initiate endpoint redirects with `INSTANCE_NOT_CONFIGURED` and the provider's `NOT_CONFIGURED` code

Run them:

```bash
docker compose -f docker-compose-test.yml run --rm api-tests pytest plane/tests/unit/authentication/ -v
```

## Verify by hand

1. Start the environment — see the `local-dev` skill
2. Enter the client ID and secret in the admin panel, section Authentication, and enable the provider
3. Sign in through the provider at `http://localhost:3000`
4. Confirm the account is created with the right email, name and avatar
5. Sign out, sign in again, and confirm the existing account is reused rather than duplicated

## Common Mistakes

- Adding the provider file but forgetting `authentication/urls.py` — the callback 404s and the provider looks broken in a way the logs don't explain
- Forgetting `license/management/commands/configure_instance.py` — `license/api/views/instance.py` works and the admin form saves credentials, but `IS_<PROVIDER>_ENABLED` is never created in the database, so the sign-in button never appears, on a fresh instance or an existing one, even with correct credentials
- Forgetting `license/api/views/instance.py` — the backend works, but the sign-in button never appears because the frontend never learns the provider is enabled
- Forgetting `utils/instance_config_variables/core.py` — works on your machine, breaks on a fresh instance where the client id/secret keys were never bootstrapped
- Forgetting the branch in `adapter/oauth.py`'s `authentication_error_code()` — provider-specific failures silently report as the generic `OAUTH_NOT_CONFIGURED` code instead of `<PROVIDER>_OAUTH_PROVIDER_ERROR`
- Adding the app views but not the space views — sign-in works in the app and 404s on public pages
- Hardcoding user-facing strings instead of routing them through `packages/i18n`
- Committing real client secrets — they belong in `.env` only
- Accepting a sign-in with no email — fail closed, as `yandex.py` and `vk.py` do
