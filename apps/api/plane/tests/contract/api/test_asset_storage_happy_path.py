# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Happy-path contract tests for the three ``S3Storage`` call sites in
``plane.api.views.asset``.

``test_generic_asset.py`` covers the cross-workspace IDOR fix, but every one
of its requests is rejected by the permission check before execution ever
reaches ``S3Storage(...)``. That left the three call sites in this module
untested against actual invocation, so a call site that had drifted out of
sync with ``S3Storage.__init__`` (which accepts only ``request``) went
unnoticed: ``asset.py`` called it with a stray ``is_server=True`` keyword,
and every one of these three routes raised ``TypeError`` on every real
request.

These tests use ``autospec=True`` when patching ``S3Storage`` specifically
because a plain ``mock.patch`` swaps in a ``MagicMock`` that accepts any
keyword argument and would happily swallow ``is_server=True`` — it would
never have caught this bug. Autospeccing makes the mock enforce the real
class's ``__init__`` signature, so it fails with the same ``TypeError`` the
real class raises, while still avoiding a real S3/MinIO round trip (the
same tradeoff ``test_generic_asset.py`` makes with its plain mocks).
"""

from unittest import mock

import pytest
from django.core.cache import cache
from rest_framework import status

from plane.db.models import FileAsset


@pytest.fixture(autouse=True)
def _reset_api_key_rate_limit(api_token):
    """``ApiKeyRateThrottle`` (see ``plane.api.rate_limit``) keys its cache
    entry on the raw token string, and the shared ``api_token`` fixture in
    the top-level conftest hardcodes that string to the same value for every
    test in the suite. That means the throttle budget is a single shared
    counter across the whole session, not per-test. Each test below makes a
    real request through it, and left alone those requests accumulate on top
    of whatever every other suite already used, eventually tipping unrelated
    later tests into 429s. Reset the counter this file consumed once each
    test finishes so it leaves no residue for tests that run after it.
    """
    yield
    cache.delete(f"api_key:{api_token.token}")


@pytest.mark.contract
class TestAssetStorageHappyPath:
    """Successful requests that actually reach ``S3Storage`` and get back a
    presigned URL, for all three broken call sites."""

    @pytest.mark.django_db
    def test_user_server_asset_post_returns_presigned_upload_url(self, api_key_client):
        """``UserServerAssetEndpoint.post`` (asset.py line 338): server-side
        presigned upload URL for a user avatar/cover asset."""
        url = "/api/v1/assets/user-assets/server/"
        payload = {
            "name": "avatar.png",
            "type": "image/png",
            "size": 2048,
            "entity_type": "USER_AVATAR",
        }

        with mock.patch("plane.api.views.asset.S3Storage", autospec=True) as mock_storage_cls:
            mock_storage_cls.return_value.generate_presigned_post.return_value = {
                "url": "https://storage.example/bucket",
                "fields": {"key": "avatar.png"},
            }
            response = api_key_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK, f"Got {response.status_code}: {response.data!r}"
        assert response.data["upload_data"] == {
            "url": "https://storage.example/bucket",
            "fields": {"key": "avatar.png"},
        }
        assert "asset_id" in response.data
        assert FileAsset.objects.filter(id=response.data["asset_id"]).exists()

        # Constructed with only the argument S3Storage.__init__ accepts.
        mock_storage_cls.assert_called_once()
        _, kwargs = mock_storage_cls.call_args
        assert "is_server" not in kwargs
        mock_storage_cls.return_value.generate_presigned_post.assert_called_once()

    @pytest.mark.django_db
    def test_generic_asset_get_returns_presigned_download_url(self, api_key_client, workspace, create_user):
        """``GenericAssetEndpoint.get`` (asset.py line 451): presigned GET for
        an already-uploaded workspace asset, requested by an active member."""
        asset = FileAsset.objects.create(
            attributes={"name": "report.pdf", "type": "application/pdf", "size": 4096},
            asset=f"{workspace.id}/report.pdf",
            size=4096,
            workspace=workspace,
            created_by=create_user,
            entity_type=FileAsset.EntityTypeContext.ISSUE_ATTACHMENT,
            is_uploaded=True,
            storage_metadata={"size": 4096},
        )
        url = f"/api/v1/workspaces/{workspace.slug}/assets/{asset.id}/"

        with mock.patch("plane.api.views.asset.S3Storage", autospec=True) as mock_storage_cls:
            mock_storage_cls.return_value.generate_presigned_url.return_value = (
                "https://storage.example/bucket/report.pdf?signature=abc"
            )
            response = api_key_client.get(url)

        assert response.status_code == status.HTTP_200_OK, f"Got {response.status_code}: {response.data!r}"
        assert response.data["asset_url"] == "https://storage.example/bucket/report.pdf?signature=abc"
        assert response.data["asset_id"] == str(asset.id)

        mock_storage_cls.assert_called_once()
        _, kwargs = mock_storage_cls.call_args
        assert "is_server" not in kwargs
        mock_storage_cls.return_value.generate_presigned_url.assert_called_once()

    @pytest.mark.django_db
    def test_generic_asset_post_returns_presigned_upload_url(self, api_key_client, workspace):
        """``GenericAssetEndpoint.post`` (asset.py line 581): presigned upload
        URL for a new generic workspace asset, requested by an active member."""
        url = f"/api/v1/workspaces/{workspace.slug}/assets/"
        payload = {"name": "diagram.png", "type": "image/png", "size": 8192}

        with mock.patch("plane.api.views.asset.S3Storage", autospec=True) as mock_storage_cls:
            mock_storage_cls.return_value.generate_presigned_post.return_value = {
                "url": "https://storage.example/bucket",
                "fields": {"key": "diagram.png"},
            }
            response = api_key_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK, f"Got {response.status_code}: {response.data!r}"
        assert response.data["upload_data"] == {
            "url": "https://storage.example/bucket",
            "fields": {"key": "diagram.png"},
        }
        assert "asset_id" in response.data
        assert FileAsset.objects.filter(id=response.data["asset_id"], workspace=workspace).exists()

        mock_storage_cls.assert_called_once()
        _, kwargs = mock_storage_cls.call_args
        assert "is_server" not in kwargs
        mock_storage_cls.return_value.generate_presigned_post.assert_called_once()
