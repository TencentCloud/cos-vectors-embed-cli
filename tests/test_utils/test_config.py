"""Tests for cos_vectors.utils.config."""

import os
from unittest.mock import patch

import pytest

from tests.constants import FAKE_SECRET_ID, FAKE_SECRET_KEY, FAKE_TOKEN
from cos_vectors.utils.config import (
    get_cos_config,
    get_cos_s3_config,
    get_domain,
    get_region,
    get_user_agent,
)


# ── get_region ─────────────────────────────────────────────────────

class TestGetRegion:
    def test_from_parameter(self):
        with patch.dict(os.environ, {"COS_REGION": "ap-guangzhou"}, clear=False):
            assert get_region("ap-beijing") == "ap-beijing"

    def test_from_env_var(self):
        with patch.dict(os.environ, {"COS_REGION": "ap-guangzhou"}, clear=False):
            assert get_region(None) == "ap-guangzhou"

    def test_missing_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Region is required"):
                get_region(None)


# ── get_domain ─────────────────────────────────────────────────────

class TestGetDomain:
    def test_from_parameter(self):
        with patch.dict(os.environ, {"COS_DOMAIN": "default.com"}, clear=False):
            assert get_domain("custom.com") == "custom.com"

    def test_from_parameter_takes_priority_over_region(self):
        with patch.dict(os.environ, {}, clear=True):
            assert get_domain("custom.com", region="ap-guangzhou") == "custom.com"

    def test_from_env_var(self):
        with patch.dict(os.environ, {"COS_DOMAIN": "vectors.ap-guangzhou.coslake.com"}, clear=False):
            assert get_domain(None) == "vectors.ap-guangzhou.coslake.com"

    def test_from_env_var_takes_priority_over_region(self):
        with patch.dict(os.environ, {"COS_DOMAIN": "env.domain.com"}, clear=False):
            assert get_domain(None, region="ap-guangzhou") == "env.domain.com"

    def test_auto_assembled_from_region(self):
        with patch.dict(os.environ, {}, clear=True):
            assert get_domain(None, region="ap-guangzhou") == "vectors.ap-guangzhou.coslake.com"

    def test_auto_assembled_from_region_ap_beijing(self):
        with patch.dict(os.environ, {}, clear=True):
            assert get_domain(None, region="ap-beijing") == "vectors.ap-beijing.coslake.com"

    def test_missing_all_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Domain is required"):
                get_domain(None)

    def test_missing_all_with_none_region_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="--region"):
                get_domain(None, region=None)


# ── get_cos_config ─────────────────────────────────────────────────

class TestGetCosConfig:
    @patch("cos_vectors.utils.config.CosConfig")
    def test_with_explicit_credentials(self, mock_cos_config):
        get_cos_config(
            region="ap-guangzhou",
            domain="vectors.test.com",
            secret_id=FAKE_SECRET_ID,
            secret_key=FAKE_SECRET_KEY,
        )
        mock_cos_config.assert_called_once_with(
            Region="ap-guangzhou",
            SecretId=FAKE_SECRET_ID,
            SecretKey=FAKE_SECRET_KEY,
            Token=None,
            Domain="vectors.test.com",
        )

    @patch("cos_vectors.utils.config.CosConfig")
    def test_with_env_credentials(self, mock_cos_config):
        with patch.dict(os.environ, {
            "COS_SECRET_ID": FAKE_SECRET_ID,
            "COS_SECRET_KEY": FAKE_SECRET_KEY,
        }, clear=False):
            get_cos_config(region="ap-guangzhou", domain="test.com")
            call_kwargs = mock_cos_config.call_args[1]
            assert call_kwargs["SecretId"] == FAKE_SECRET_ID
            assert call_kwargs["SecretKey"] == FAKE_SECRET_KEY

    def test_missing_credentials_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="COS credentials are required"):
                get_cos_config(region="ap-guangzhou", domain="test.com")

    @patch("cos_vectors.utils.config.CosConfig")
    def test_with_token(self, mock_cos_config):
        get_cos_config(
            region="ap-guangzhou",
            domain="test.com",
            secret_id=FAKE_SECRET_ID,
            secret_key=FAKE_SECRET_KEY,
            token=FAKE_TOKEN,
        )
        call_kwargs = mock_cos_config.call_args[1]
        assert call_kwargs["Token"] == FAKE_TOKEN


# ── get_cos_s3_config ──────────────────────────────────────────────

class TestGetCosS3Config:
    @patch("cos_vectors.utils.config.CosConfig")
    def test_with_region(self, mock_cos_config):
        with patch.dict(os.environ, {
            "COS_SECRET_ID": FAKE_SECRET_ID,
            "COS_SECRET_KEY": FAKE_SECRET_KEY,
        }, clear=False):
            get_cos_s3_config(region="ap-guangzhou")
            mock_cos_config.assert_called_once_with(
                Region="ap-guangzhou",
                SecretId=FAKE_SECRET_ID,
                SecretKey=FAKE_SECRET_KEY,
                Token=None,
            )

    def test_missing_credentials_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="COS credentials are required"):
                get_cos_s3_config(region="ap-guangzhou")


# ── get_user_agent ─────────────────────────────────────────────────

class TestGetUserAgent:
    def test_format(self):
        ua = get_user_agent()
        assert ua.startswith("cos-vectors-embed/")
