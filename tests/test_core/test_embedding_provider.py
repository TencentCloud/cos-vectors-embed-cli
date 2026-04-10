"""Tests for cos_vectors.core.embedding_provider."""

import json
from unittest.mock import MagicMock, patch

import pytest

from tests.constants import FAKE_API_KEY
from cos_vectors.core.embedding_provider import (
    EmbeddingAPIError,
    OpenAICompatibleProvider,
    get_provider,
)


# ── get_provider factory ───────────────────────────────────────────

class TestGetProvider:
    def test_openai_compatible(self):
        provider = get_provider(
            provider_type="openai-compatible",
            api_base="http://localhost:11434/v1",
            api_key=FAKE_API_KEY,
        )
        assert isinstance(provider, OpenAICompatibleProvider)

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown provider type"):
            get_provider(provider_type="unknown", api_base="x", api_key=FAKE_API_KEY)

    def test_error_message_lists_supported(self):
        with pytest.raises(ValueError, match="openai-compatible"):
            get_provider(provider_type="bad")


# ── OpenAICompatibleProvider ───────────────────────────────────────

class TestOpenAICompatibleProvider:
    def _make_provider(self, **kwargs):
        defaults = {
            "api_base": "http://localhost:11434/v1",
            "api_key": FAKE_API_KEY,
            "default_model": "test-model",
        }
        defaults.update(kwargs)
        return OpenAICompatibleProvider(**defaults)

    def _mock_urlopen_response(self, response_data):
        """Create a mock context manager for urllib.request.urlopen."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(response_data).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        return mock_response

    def test_embed_texts_single(self):
        provider = self._make_provider()
        response_data = {
            "data": [{"index": 0, "embedding": [0.1, 0.2, 0.3]}],
        }
        mock_resp = self._mock_urlopen_response(response_data)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = provider.embed_texts(["hello world"], model="test-model")

        assert result == [[0.1, 0.2, 0.3]]

    def test_embed_texts_batch(self):
        provider = self._make_provider()
        response_data = {
            "data": [
                {"index": 0, "embedding": [0.1, 0.2]},
                {"index": 1, "embedding": [0.3, 0.4]},
            ],
        }
        mock_resp = self._mock_urlopen_response(response_data)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = provider.embed_texts(["text1", "text2"])

        assert len(result) == 2
        assert result[0] == [0.1, 0.2]
        assert result[1] == [0.3, 0.4]

    def test_embed_texts_sorts_by_index(self):
        """Verify that results are sorted by index even if API returns out of order."""
        provider = self._make_provider()
        response_data = {
            "data": [
                {"index": 1, "embedding": [0.3, 0.4]},
                {"index": 0, "embedding": [0.1, 0.2]},
            ],
        }
        mock_resp = self._mock_urlopen_response(response_data)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = provider.embed_texts(["text1", "text2"])

        assert result[0] == [0.1, 0.2]  # index 0 first
        assert result[1] == [0.3, 0.4]  # index 1 second

    def test_embed_texts_with_dimensions(self):
        provider = self._make_provider()
        response_data = {
            "data": [{"index": 0, "embedding": [0.1]}],
        }
        mock_resp = self._mock_urlopen_response(response_data)

        with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
            provider.embed_texts(["test"], dimensions=128)

            # Verify dimensions was sent in payload
            call_args = mock_urlopen.call_args
            request_obj = call_args[0][0]
            payload = json.loads(request_obj.data.decode("utf-8"))
            assert payload["dimensions"] == 128

    def test_embed_image(self):
        provider = self._make_provider()
        response_data = {
            "data": [{"index": 0, "embedding": [0.4, 0.5, 0.6]}],
        }
        mock_resp = self._mock_urlopen_response(response_data)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = provider.embed_image("base64string", model="test-model")

        assert result == [0.4, 0.5, 0.6]

    def test_api_error_http_429(self):
        import urllib.error

        provider = self._make_provider()
        http_error = urllib.error.HTTPError(
            url="http://test",
            code=429,
            msg="Rate Limit",
            hdrs=MagicMock(),
            fp=MagicMock(),
        )
        http_error.read = MagicMock(return_value=b"rate limited")

        with patch("urllib.request.urlopen", side_effect=http_error):
            with pytest.raises(EmbeddingAPIError) as exc_info:
                provider.embed_texts(["test"])

            assert exc_info.value.status_code == 429

    def test_connection_error(self):
        import urllib.error

        provider = self._make_provider()
        url_error = urllib.error.URLError("Connection refused")

        with patch("urllib.request.urlopen", side_effect=url_error):
            with pytest.raises(ConnectionError, match="Failed to connect"):
                provider.embed_texts(["test"])

    def test_api_base_trailing_slash_stripped(self):
        provider = self._make_provider(api_base="http://localhost:11434/v1/")
        assert provider._embeddings_url == "http://localhost:11434/v1/embeddings"

    def test_authorization_header(self):
        provider = self._make_provider(api_key=FAKE_API_KEY)
        response_data = {"data": [{"index": 0, "embedding": [0.1]}]}
        mock_resp = self._mock_urlopen_response(response_data)

        with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
            provider.embed_texts(["test"])

            request_obj = mock_urlopen.call_args[0][0]
            assert request_obj.get_header("Authorization") == f"Bearer {FAKE_API_KEY}"


# ── EmbeddingAPIError ──────────────────────────────────────────────

class TestEmbeddingAPIError:
    def test_attributes(self):
        err = EmbeddingAPIError(status_code=500, message="Internal error")
        assert err.status_code == 500
        assert err.message == "Internal error"

    def test_str_repr(self):
        err = EmbeddingAPIError(status_code=429, message="Rate limited")
        assert "429" in str(err)
        assert "Rate limited" in str(err)
