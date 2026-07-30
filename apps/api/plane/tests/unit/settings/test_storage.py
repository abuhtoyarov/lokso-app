# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import os
from unittest.mock import Mock, patch
import pytest
from django.test import RequestFactory
from plane.settings.storage import S3Storage


@pytest.mark.unit
class TestS3StorageSignedURLExpiration:
    """Test the configurable signed URL expiration in S3Storage"""

    @patch.dict(os.environ, {}, clear=True)
    @patch("plane.settings.storage.boto3")
    def test_default_expiration_without_env_variable(self, mock_boto3):
        """Test that default expiration is 3600 seconds when env variable is not set"""
        # Mock the boto3 client
        mock_boto3.client.return_value = Mock()

        # Create S3Storage instance without SIGNED_URL_EXPIRATION env variable
        storage = S3Storage()

        # Assert default expiration is 3600
        assert storage.signed_url_expiration == 3600

    @patch.dict(os.environ, {"SIGNED_URL_EXPIRATION": "30"}, clear=True)
    @patch("plane.settings.storage.boto3")
    def test_custom_expiration_with_env_variable(self, mock_boto3):
        """Test that expiration is read from SIGNED_URL_EXPIRATION env variable"""
        # Mock the boto3 client
        mock_boto3.client.return_value = Mock()

        # Create S3Storage instance with SIGNED_URL_EXPIRATION=30
        storage = S3Storage()

        # Assert expiration is 30
        assert storage.signed_url_expiration == 30

    @patch.dict(os.environ, {"SIGNED_URL_EXPIRATION": "300"}, clear=True)
    @patch("plane.settings.storage.boto3")
    def test_custom_expiration_multiple_values(self, mock_boto3):
        """Test that expiration works with different custom values"""
        # Mock the boto3 client
        mock_boto3.client.return_value = Mock()

        # Create S3Storage instance with SIGNED_URL_EXPIRATION=300
        storage = S3Storage()

        # Assert expiration is 300
        assert storage.signed_url_expiration == 300

    @patch.dict(
        os.environ,
        {
            "AWS_ACCESS_KEY_ID": "test-key",
            "AWS_SECRET_ACCESS_KEY": "test-secret",
            "AWS_S3_BUCKET_NAME": "test-bucket",
            "AWS_REGION": "us-east-1",
        },
        clear=True,
    )
    @patch("plane.settings.storage.boto3")
    def test_generate_presigned_post_uses_default_expiration(self, mock_boto3):
        """Test that generate_presigned_post uses the configured default expiration"""
        # Mock the boto3 client and its response
        mock_s3_client = Mock()
        mock_s3_client.generate_presigned_post.return_value = {
            "url": "https://test-url.com",
            "fields": {},
        }
        mock_boto3.client.return_value = mock_s3_client

        # Create S3Storage instance
        storage = S3Storage()

        # Call generate_presigned_post without explicit expiration
        storage.generate_presigned_post("test-object", "image/png", 1024)

        # Assert that the boto3 method was called with the default expiration (3600)
        mock_s3_client.generate_presigned_post.assert_called_once()
        call_kwargs = mock_s3_client.generate_presigned_post.call_args[1]
        assert call_kwargs["ExpiresIn"] == 3600

    @patch.dict(
        os.environ,
        {
            "AWS_ACCESS_KEY_ID": "test-key",
            "AWS_SECRET_ACCESS_KEY": "test-secret",
            "AWS_S3_BUCKET_NAME": "test-bucket",
            "AWS_REGION": "us-east-1",
            "SIGNED_URL_EXPIRATION": "60",
        },
        clear=True,
    )
    @patch("plane.settings.storage.boto3")
    def test_generate_presigned_post_uses_custom_expiration(self, mock_boto3):
        """Test that generate_presigned_post uses custom expiration from env variable"""
        # Mock the boto3 client and its response
        mock_s3_client = Mock()
        mock_s3_client.generate_presigned_post.return_value = {
            "url": "https://test-url.com",
            "fields": {},
        }
        mock_boto3.client.return_value = mock_s3_client

        # Create S3Storage instance with SIGNED_URL_EXPIRATION=60
        storage = S3Storage()

        # Call generate_presigned_post without explicit expiration
        storage.generate_presigned_post("test-object", "image/png", 1024)

        # Assert that the boto3 method was called with custom expiration (60)
        mock_s3_client.generate_presigned_post.assert_called_once()
        call_kwargs = mock_s3_client.generate_presigned_post.call_args[1]
        assert call_kwargs["ExpiresIn"] == 60

    @patch.dict(
        os.environ,
        {
            "AWS_ACCESS_KEY_ID": "test-key",
            "AWS_SECRET_ACCESS_KEY": "test-secret",
            "AWS_S3_BUCKET_NAME": "test-bucket",
            "AWS_REGION": "us-east-1",
        },
        clear=True,
    )
    @patch("plane.settings.storage.boto3")
    def test_generate_presigned_url_uses_default_expiration(self, mock_boto3):
        """Test that generate_presigned_url uses the configured default expiration"""
        # Mock the boto3 client and its response
        mock_s3_client = Mock()
        mock_s3_client.generate_presigned_url.return_value = "https://test-url.com"
        mock_boto3.client.return_value = mock_s3_client

        # Create S3Storage instance
        storage = S3Storage()

        # Call generate_presigned_url without explicit expiration
        storage.generate_presigned_url("test-object")

        # Assert that the boto3 method was called with the default expiration (3600)
        mock_s3_client.generate_presigned_url.assert_called_once()
        call_kwargs = mock_s3_client.generate_presigned_url.call_args[1]
        assert call_kwargs["ExpiresIn"] == 3600

    @patch.dict(
        os.environ,
        {
            "AWS_ACCESS_KEY_ID": "test-key",
            "AWS_SECRET_ACCESS_KEY": "test-secret",
            "AWS_S3_BUCKET_NAME": "test-bucket",
            "AWS_REGION": "us-east-1",
            "SIGNED_URL_EXPIRATION": "30",
        },
        clear=True,
    )
    @patch("plane.settings.storage.boto3")
    def test_generate_presigned_url_uses_custom_expiration(self, mock_boto3):
        """Test that generate_presigned_url uses custom expiration from env variable"""
        # Mock the boto3 client and its response
        mock_s3_client = Mock()
        mock_s3_client.generate_presigned_url.return_value = "https://test-url.com"
        mock_boto3.client.return_value = mock_s3_client

        # Create S3Storage instance with SIGNED_URL_EXPIRATION=30
        storage = S3Storage()

        # Call generate_presigned_url without explicit expiration
        storage.generate_presigned_url("test-object")

        # Assert that the boto3 method was called with custom expiration (30)
        mock_s3_client.generate_presigned_url.assert_called_once()
        call_kwargs = mock_s3_client.generate_presigned_url.call_args[1]
        assert call_kwargs["ExpiresIn"] == 30

    @patch.dict(
        os.environ,
        {
            "AWS_ACCESS_KEY_ID": "test-key",
            "AWS_SECRET_ACCESS_KEY": "test-secret",
            "AWS_S3_BUCKET_NAME": "test-bucket",
            "AWS_REGION": "us-east-1",
            "SIGNED_URL_EXPIRATION": "30",
        },
        clear=True,
    )
    @patch("plane.settings.storage.boto3")
    def test_explicit_expiration_overrides_default(self, mock_boto3):
        """Test that explicit expiration parameter overrides the default"""
        # Mock the boto3 client and its response
        mock_s3_client = Mock()
        mock_s3_client.generate_presigned_url.return_value = "https://test-url.com"
        mock_boto3.client.return_value = mock_s3_client

        # Create S3Storage instance with SIGNED_URL_EXPIRATION=30
        storage = S3Storage()

        # Call generate_presigned_url with explicit expiration=120
        storage.generate_presigned_url("test-object", expiration=120)

        # Assert that the boto3 method was called with explicit expiration (120)
        mock_s3_client.generate_presigned_url.assert_called_once()
        call_kwargs = mock_s3_client.generate_presigned_url.call_args[1]
        assert call_kwargs["ExpiresIn"] == 120


# The storage layer serves two audiences with different addresses.
#
# Presigned URLs are handed to a browser and must point somewhere the browser
# can reach. Server-side calls run inside the network and must not go out
# through the public host. One client cannot do both.


def _request():
    return RequestFactory().post("/api/assets/", HTTP_HOST="localhost:8000")


@pytest.fixture
def minio_env(monkeypatch):
    """MinIO enabled, internal endpoint set, no public endpoint configured."""
    monkeypatch.setenv("USE_MINIO", "1")
    monkeypatch.setenv("AWS_S3_ENDPOINT_URL", "http://plane-minio:9000")
    monkeypatch.setenv("AWS_S3_BUCKET_NAME", "uploads")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-key")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.delenv("MINIO_PUBLIC_ENDPOINT_URL", raising=False)
    monkeypatch.delenv("MINIO_ENDPOINT_SSL", raising=False)


@pytest.mark.unit
def test_server_client_ignores_the_request_host(minio_env):
    """Server-side calls must reach storage directly, never via the public host."""
    storage = S3Storage(request=_request())
    assert storage.s3_client.meta.endpoint_url == "http://plane-minio:9000"


@pytest.mark.unit
def test_presigned_client_uses_the_request_host_by_default(minio_env):
    """Production behaviour, unchanged: same origin as the request, which the
    proxy then routes to storage."""
    storage = S3Storage(request=_request())
    assert storage.presigned_client.meta.endpoint_url == "http://localhost:8000"


@pytest.mark.unit
def test_public_endpoint_overrides_the_request_host(minio_env, monkeypatch):
    """Local development: no proxy, so the browser is told where MinIO really is."""
    monkeypatch.setenv("MINIO_PUBLIC_ENDPOINT_URL", "http://localhost:9000")
    storage = S3Storage(request=_request())
    assert storage.presigned_client.meta.endpoint_url == "http://localhost:9000"
    assert storage.s3_client.meta.endpoint_url == "http://plane-minio:9000"


@pytest.mark.unit
def test_presigned_client_falls_back_to_the_internal_endpoint(minio_env):
    """Background tasks have no request and no browser to serve."""
    storage = S3Storage()
    assert storage.presigned_client.meta.endpoint_url == "http://plane-minio:9000"


@pytest.mark.unit
def test_public_endpoint_applies_without_a_request(minio_env, monkeypatch):
    monkeypatch.setenv("MINIO_PUBLIC_ENDPOINT_URL", "http://localhost:9000")
    storage = S3Storage()
    assert storage.presigned_client.meta.endpoint_url == "http://localhost:9000"


@pytest.mark.unit
def test_ssl_flag_still_governs_the_request_derived_scheme(minio_env, monkeypatch):
    monkeypatch.setenv("MINIO_ENDPOINT_SSL", "1")
    storage = S3Storage(request=_request())
    assert storage.presigned_client.meta.endpoint_url == "https://localhost:8000"


@pytest.mark.unit
def test_real_s3_is_untouched(monkeypatch):
    """USE_MINIO=0 means a real S3 endpoint; neither client derives from the request."""
    monkeypatch.setenv("USE_MINIO", "0")
    monkeypatch.setenv("AWS_S3_ENDPOINT_URL", "https://s3.example.com")
    monkeypatch.setenv("AWS_S3_BUCKET_NAME", "uploads")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-key")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("MINIO_PUBLIC_ENDPOINT_URL", "http://localhost:9000")

    storage = S3Storage(request=_request())
    assert storage.s3_client.meta.endpoint_url == "https://s3.example.com"
    assert storage.presigned_client.meta.endpoint_url == "https://s3.example.com"


@pytest.mark.unit
def test_presigned_post_url_points_at_the_public_endpoint(minio_env, monkeypatch):
    """The end result a browser receives, not just the client configuration."""
    monkeypatch.setenv("MINIO_PUBLIC_ENDPOINT_URL", "http://localhost:9000")
    storage = S3Storage(request=_request())
    post = storage.generate_presigned_post("cover.png", "image/png", 1000)
    assert post["url"].startswith("http://localhost:9000")


@pytest.mark.unit
def test_presigned_download_url_points_at_the_public_endpoint(minio_env, monkeypatch):
    monkeypatch.setenv("MINIO_PUBLIC_ENDPOINT_URL", "http://localhost:9000")
    storage = S3Storage(request=_request())
    url = storage.generate_presigned_url("cover.png")
    assert url.startswith("http://localhost:9000")


@pytest.mark.unit
def test_presigned_download_url_matches_production_when_public_endpoint_is_unset(minio_env):
    """The requirement that governs this whole change: with MINIO_PUBLIC_ENDPOINT_URL
    unset, a presigned URL in production is unchanged. Assert that at the level a
    user actually experiences it -- the URL itself -- not just the client's
    endpoint configuration."""
    storage = S3Storage(request=_request())
    url = storage.generate_presigned_url("cover.png")
    assert url.startswith("http://localhost:8000")


@pytest.mark.unit
def test_server_client_falls_back_to_the_request_host_when_no_internal_endpoint_is_configured(monkeypatch):
    """Before the client split, one request-scoped instance derived a working
    endpoint from the request host, so USE_MINIO=1 with neither AWS_S3_ENDPOINT_URL
    nor MINIO_ENDPOINT_URL set still worked. The split broke that: s3_client was
    built with endpoint_url=None and boto3 fell through to a bogus AWS default,
    raising ValueError. Pin the fix: construction must not raise, and the server
    client must fall back to the same host the presigned client resolves to."""
    monkeypatch.setenv("USE_MINIO", "1")
    monkeypatch.delenv("AWS_S3_ENDPOINT_URL", raising=False)
    monkeypatch.delenv("MINIO_ENDPOINT_URL", raising=False)
    monkeypatch.delenv("MINIO_PUBLIC_ENDPOINT_URL", raising=False)
    monkeypatch.delenv("MINIO_ENDPOINT_SSL", raising=False)
    monkeypatch.setenv("AWS_S3_BUCKET_NAME", "uploads")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-key")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret")
    monkeypatch.setenv("AWS_REGION", "us-east-1")

    storage = S3Storage(request=_request())

    assert storage.s3_client.meta.endpoint_url == "http://localhost:8000"


@pytest.mark.unit
def test_reuses_one_client_when_endpoints_match(monkeypatch):
    """When the resolved presigned endpoint equals the internal endpoint, building
    two identical boto3 clients is pure overhead on a call path (request-scoped
    instantiation) that runs on every asset request."""
    monkeypatch.setenv("USE_MINIO", "1")
    monkeypatch.setenv("AWS_S3_ENDPOINT_URL", "http://plane-minio:9000")
    monkeypatch.setenv("MINIO_PUBLIC_ENDPOINT_URL", "http://plane-minio:9000")
    monkeypatch.setenv("AWS_S3_BUCKET_NAME", "uploads")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-key")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret")
    monkeypatch.setenv("AWS_REGION", "us-east-1")

    storage = S3Storage(request=_request())

    assert storage.s3_client is storage.presigned_client


@pytest.mark.unit
def test_server_methods_use_the_server_client_not_the_presigned_client(minio_env):
    """upload_file, delete_files, copy_object and get_object_metadata are
    server-side calls and must go out through s3_client. This is the entire
    point of the client split -- upload_file is the OAuth-avatar path the split
    exists to fix -- so pin it with an assertion that can actually catch a swap.
    The other tests in this module mock boto3 wholesale, which makes s3_client
    and presigned_client the same mock and can't detect a method wired to the
    wrong one; here the two endpoints differ, so each client is a distinct mock
    object and we can assert on which one a call reached."""
    with patch("plane.settings.storage.boto3") as mock_boto3:
        mock_boto3.client.side_effect = lambda *args, **kwargs: Mock()
        storage = S3Storage(request=_request())

        # Sanity check that the test setup can actually distinguish the two.
        assert storage.s3_client is not storage.presigned_client

        storage.upload_file(Mock(), "object.png")
        storage.delete_files(["object.png"])
        storage.copy_object("object.png", "object-copy.png")
        storage.get_object_metadata("object.png")

    storage.s3_client.upload_fileobj.assert_called_once()
    storage.s3_client.delete_objects.assert_called_once()
    storage.s3_client.copy_object.assert_called_once()
    storage.s3_client.head_object.assert_called_once()

    storage.presigned_client.upload_fileobj.assert_not_called()
    storage.presigned_client.delete_objects.assert_not_called()
    storage.presigned_client.copy_object.assert_not_called()
    storage.presigned_client.head_object.assert_not_called()
