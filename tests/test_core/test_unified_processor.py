"""Tests for cos_vectors.core.unified_processor."""

from unittest.mock import MagicMock

import pytest

from cos_vectors.core.unified_processor import ProcessingResult, UnifiedProcessor
from cos_vectors.utils.models import ProcessingInput


class TestUnifiedProcessor:
    """Tests for UnifiedProcessor."""

    def _make_processor(
        self,
        mock_embedding_provider=None,
        mock_cos_service=None,
        cos_s3_client=None,
    ):
        provider = mock_embedding_provider or MagicMock()
        provider.embed_texts.return_value = [[0.1, 0.2, 0.3]]
        provider.embed_image.return_value = [0.4, 0.5, 0.6]

        service = mock_cos_service or MagicMock()
        service.get_index.return_value = {"dimension": 3}

        return UnifiedProcessor(
            embedding_provider=provider,
            cos_service=service,
            model_id="test-model",
            console=MagicMock(),
            cos_s3_client=cos_s3_client,
        )


class TestPrepareContent:
    """Tests for UnifiedProcessor._prepare_content."""

    def _make_processor(self, cos_s3_client=None):
        provider = MagicMock()
        service = MagicMock()
        return UnifiedProcessor(
            embedding_provider=provider,
            cos_service=service,
            model_id="test-model",
            console=MagicMock(),
            cos_s3_client=cos_s3_client,
        )

    def test_text_value_direct(self):
        processor = self._make_processor()
        inp = ProcessingInput(content_type="text", data="hello world")
        result = processor._prepare_content(inp)
        assert result == "hello world"

    def test_local_text_file(self, tmp_text_file):
        processor = self._make_processor()
        inp = ProcessingInput(
            content_type="text",
            data=None,
            source_location=tmp_text_file,
        )
        result = processor._prepare_content(inp)
        assert result == "test content"

    def test_cos_uri_text(self):
        mock_s3 = MagicMock()
        mock_stream = MagicMock()
        mock_stream.read.return_value = b"cos text content"
        mock_body = MagicMock()
        mock_body.get_raw_stream.return_value = mock_stream
        mock_s3.get_object.return_value = {"Body": mock_body}

        processor = self._make_processor(cos_s3_client=mock_s3)
        inp = ProcessingInput(
            content_type="text",
            data=None,
            source_location="cos://mybucket/path/to/file.txt",
        )
        result = processor._prepare_content(inp)
        assert result == "cos text content"
        mock_s3.get_object.assert_called_once_with(
            Bucket="mybucket", Key="path/to/file.txt"
        )

    def test_cos_uri_without_client_raises(self):
        processor = self._make_processor(cos_s3_client=None)
        inp = ProcessingInput(
            content_type="text",
            data=None,
            source_location="cos://mybucket/file.txt",
        )
        with pytest.raises(ValueError, match="COS S3 client not configured"):
            processor._prepare_content(inp)

    def test_no_data_no_source_raises(self):
        processor = self._make_processor()
        inp = ProcessingInput(content_type="text", data=None, source_location=None)
        with pytest.raises(ValueError, match="No data or source_location"):
            processor._prepare_content(inp)


class TestProcess:
    """Tests for the full process() pipeline."""

    def _make_processor(self, mock_embedding_provider=None, mock_cos_service=None):
        provider = mock_embedding_provider or MagicMock()
        provider.embed_texts.return_value = [[0.1, 0.2, 0.3]]

        service = mock_cos_service or MagicMock()
        service.get_index.return_value = {"dimension": 3}

        return UnifiedProcessor(
            embedding_provider=provider,
            cos_service=service,
            model_id="test-model",
            console=MagicMock(),
        )

    def test_full_pipeline_text_value(self):
        processor = self._make_processor()
        inp = ProcessingInput(
            content_type="text",
            data="hello world",
            source_location="inline",
        )

        result = processor.process(inp, bucket_name="bucket", index_name="index")

        assert isinstance(result, ProcessingResult)
        assert result.content_type == "text"
        assert len(result.vectors) == 1
        assert result.vectors[0]["data"]["float32"] == [0.1, 0.2, 0.3]
        assert "key" in result.vectors[0]

    def test_full_pipeline_with_custom_key(self):
        processor = self._make_processor()
        inp = ProcessingInput(
            content_type="text",
            data="hello",
            custom_key="my-custom-key",
        )

        result = processor.process(inp, bucket_name="b", index_name="i")

        assert result.vectors[0]["key"] == "my-custom-key"

    def test_full_pipeline_with_metadata(self):
        processor = self._make_processor()
        inp = ProcessingInput(
            content_type="text",
            data="hello",
            metadata={"category": "test"},
        )

        result = processor.process(inp, bucket_name="b", index_name="i")

        meta = result.vectors[0].get("metadata", {})
        assert meta.get("category") == "test"


class TestProcessQuery:
    """Tests for the process_query() method."""

    def _make_processor(self, mock_embedding_provider=None):
        provider = mock_embedding_provider or MagicMock()
        provider.embed_texts.return_value = [[0.1, 0.2, 0.3]]

        service = MagicMock()

        return UnifiedProcessor(
            embedding_provider=provider,
            cos_service=service,
            model_id="test-model",
            console=MagicMock(),
        )

    def test_query_returns_embedding(self):
        processor = self._make_processor()
        inp = ProcessingInput(content_type="text", data="search query")

        result = processor.process_query(inp)

        assert result == [0.1, 0.2, 0.3]

    def test_query_empty_embedding_raises(self):
        provider = MagicMock()
        provider.embed_texts.return_value = []

        service = MagicMock()
        processor = UnifiedProcessor(
            embedding_provider=provider,
            cos_service=service,
            model_id="test-model",
            console=MagicMock(),
        )
        inp = ProcessingInput(content_type="text", data="query")

        with pytest.raises(ValueError, match="Failed to generate embedding"):
            processor.process_query(inp)


class TestStoreVectors:
    """Tests for the store_vectors() method."""

    def test_store_empty_result(self):
        service = MagicMock()
        processor = UnifiedProcessor(
            embedding_provider=MagicMock(),
            cos_service=service,
            model_id="m",
            console=MagicMock(),
        )
        result = ProcessingResult(vectors=[])

        keys = processor.store_vectors(result, "bucket", "index")

        assert keys == []
        service.put_vectors_batch.assert_not_called()

    def test_store_calls_service(self):
        service = MagicMock()
        service.put_vectors_batch.return_value = ["key-1"]

        processor = UnifiedProcessor(
            embedding_provider=MagicMock(),
            cos_service=service,
            model_id="m",
            console=MagicMock(),
        )
        result = ProcessingResult(
            vectors=[{"key": "key-1", "data": {"float32": [0.1]}}]
        )

        keys = processor.store_vectors(result, "bucket", "index")

        assert keys == ["key-1"]
        service.put_vectors_batch.assert_called_once()
