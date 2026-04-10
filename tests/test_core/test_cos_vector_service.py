"""Tests for cos_vectors.core.cos_vector_service."""

from unittest.mock import MagicMock, patch

import pytest

from tests.constants import FAKE_SECRET_ID, FAKE_SECRET_KEY


def _make_vector(key: str):
    """Helper to create a vector dict."""
    return {
        "key": key,
        "data": {"float32": [0.1, 0.2, 0.3]},
        "metadata": {"source": "test"},
    }


def _make_service():
    """Create a COSVectorService with fully mocked COS client.

    CosVectorsClient is imported inside __init__ via
    ``from qcloud_cos import CosVectorsClient``, so we mock it at
    the qcloud_cos module level.
    """
    with patch("cos_vectors.core.cos_vector_service.get_cos_config") as mock_config, \
         patch("qcloud_cos.CosVectorsClient") as mock_client_cls:
        mock_config.return_value = MagicMock()
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        from cos_vectors.core.cos_vector_service import COSVectorService
        service = COSVectorService(
            region="ap-guangzhou",
            domain="vectors.test.com",
            secret_id=FAKE_SECRET_ID,
            secret_key=FAKE_SECRET_KEY,
        )
        return service, mock_client


# ── put_vectors_batch ──────────────────────────────────────────────

class TestPutVectorsBatch:
    def test_empty_batch(self):
        service, mock_client = _make_service()
        result = service.put_vectors_batch("bucket", "index", [])
        assert result == []
        mock_client.put_vectors.assert_not_called()

    def test_small_batch_single_call(self):
        service, mock_client = _make_service()
        vectors = [_make_vector(f"key-{i}") for i in range(100)]

        result = service.put_vectors_batch("bucket", "index", vectors)

        assert len(result) == 100
        mock_client.put_vectors.assert_called_once()

    def test_exact_limit_single_call(self):
        service, mock_client = _make_service()
        vectors = [_make_vector(f"key-{i}") for i in range(500)]

        result = service.put_vectors_batch("bucket", "index", vectors)

        assert len(result) == 500
        mock_client.put_vectors.assert_called_once()

    def test_large_batch_auto_split(self):
        service, mock_client = _make_service()
        vectors = [_make_vector(f"key-{i}") for i in range(1200)]

        result = service.put_vectors_batch("bucket", "index", vectors)

        assert len(result) == 1200
        # 1200 / 500 = 3 batches (500 + 500 + 200)
        assert mock_client.put_vectors.call_count == 3

    def test_put_vectors_batch_api_params(self):
        service, mock_client = _make_service()
        vectors = [_make_vector("test-key")]

        service.put_vectors_batch("my-bucket", "my-index", vectors)

        mock_client.put_vectors.assert_called_once_with(
            Bucket="my-bucket",
            Index="my-index",
            Vectors=vectors,
        )

    def test_put_vectors_batch_raises_on_error(self):
        service, mock_client = _make_service()
        mock_client.put_vectors.side_effect = Exception("COS API error")

        with pytest.raises(Exception, match="COS API error"):
            service.put_vectors_batch("bucket", "index", [_make_vector("k")])


# ── query_vectors ──────────────────────────────────────────────────

class TestQueryVectors:
    def test_basic_query(self):
        service, mock_client = _make_service()
        mock_client.query_vectors.return_value = ({}, [{"key": "r1"}])

        result = service.query_vectors(
            bucket_name="bucket",
            index_name="index",
            query_embedding=[0.1, 0.2, 0.3],
            top_k=5,
        )

        assert result == [{"key": "r1"}]
        call_kwargs = mock_client.query_vectors.call_args[1]
        assert call_kwargs["Bucket"] == "bucket"
        assert call_kwargs["Index"] == "index"
        assert call_kwargs["TopK"] == 5
        assert call_kwargs["QueryVector"] == {"float32": [0.1, 0.2, 0.3]}

    def test_query_with_filter(self):
        service, mock_client = _make_service()
        mock_client.query_vectors.return_value = ({}, [])

        service.query_vectors(
            bucket_name="bucket",
            index_name="index",
            query_embedding=[0.1],
            filter_expr='category = "finance"',
        )

        call_kwargs = mock_client.query_vectors.call_args[1]
        assert call_kwargs["Filter"] == 'category = "finance"'

    def test_query_return_flags(self):
        service, mock_client = _make_service()
        mock_client.query_vectors.return_value = ({}, [])

        service.query_vectors(
            bucket_name="bucket",
            index_name="index",
            query_embedding=[0.1],
            return_metadata=False,
            return_distance=False,
        )

        call_kwargs = mock_client.query_vectors.call_args[1]
        assert call_kwargs["ReturnMetaData"] is False
        assert call_kwargs["ReturnDistance"] is False


# ── get_index ──────────────────────────────────────────────────────

class TestGetIndex:
    def test_get_index(self):
        service, mock_client = _make_service()
        mock_client.get_index.return_value = ({}, {"dimension": 768, "metric": "cosine"})

        result = service.get_index("bucket", "index")

        assert result == {"dimension": 768, "metric": "cosine"}
        mock_client.get_index.assert_called_once_with(
            Bucket="bucket",
            Index="index",
        )
