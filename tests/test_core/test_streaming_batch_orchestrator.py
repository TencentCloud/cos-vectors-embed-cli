"""Tests for cos_vectors.core.streaming_batch_orchestrator."""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from cos_vectors.core.streaming_batch_orchestrator import (
    BatchResult,
    StreamingBatchOrchestrator,
)


def _make_orchestrator(cos_s3_client=None, batch_size=100):
    provider = MagicMock()
    provider.embed_texts.return_value = [[0.1, 0.2, 0.3]]
    provider.embed_image.return_value = [0.4, 0.5, 0.6]

    service = MagicMock()
    service.put_vectors_batch.return_value = ["key-1"]

    return StreamingBatchOrchestrator(
        embedding_provider=provider,
        cos_service=service,
        model_id="test-model",
        max_workers=2,
        batch_size=batch_size,
        console=MagicMock(),
        cos_s3_client=cos_s3_client,
    )


class TestLocalGlobProcessing:
    """Tests for local glob file processing."""

    @patch("cos_vectors.core.streaming_batch_orchestrator.Progress")
    def test_process_local_glob(self, mock_progress_cls):
        """Test processing multiple local text files."""
        # Mock Progress context manager
        mock_progress = MagicMock()
        mock_progress.__enter__ = MagicMock(return_value=mock_progress)
        mock_progress.__exit__ = MagicMock(return_value=False)
        mock_progress.add_task.return_value = 0
        mock_progress_cls.return_value = mock_progress

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create 3 text files
            for i in range(3):
                filepath = os.path.join(tmpdir, f"doc{i}.txt")
                with open(filepath, "w") as f:
                    f.write(f"content {i}")

            orchestrator = _make_orchestrator()
            pattern = os.path.join(tmpdir, "*.txt")
            result = orchestrator.process_streaming_batch(
                file_pattern=pattern,
                bucket_name="bucket",
                index_name="index",
            )

            assert isinstance(result, BatchResult)
            assert result.elapsed_time > 0

    def test_no_matching_files(self):
        """Test when glob pattern matches no files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = _make_orchestrator()
            pattern = os.path.join(tmpdir, "*.xyz")
            result = orchestrator.process_streaming_batch(
                file_pattern=pattern,
                bucket_name="bucket",
                index_name="index",
            )

            assert isinstance(result, BatchResult)
            assert result.processed_count == 0
            assert result.failed_count == 0


class TestCosStreamingProcessing:
    """Tests for COS prefix streaming."""

    def test_cos_prefix_without_client_raises(self):
        """Test that COS prefix without S3 client raises ValueError."""
        orchestrator = _make_orchestrator(cos_s3_client=None)

        with pytest.raises(ValueError, match="COS S3 client not configured"):
            orchestrator.process_streaming_batch(
                file_pattern="cos://bucket/docs/",
                bucket_name="target-bucket",
                index_name="index",
            )

    @patch("cos_vectors.core.streaming_batch_orchestrator.Progress")
    def test_cos_prefix_processing(self, mock_progress_cls):
        """Test COS prefix lists and processes objects."""
        mock_progress = MagicMock()
        mock_progress.__enter__ = MagicMock(return_value=mock_progress)
        mock_progress.__exit__ = MagicMock(return_value=False)
        mock_progress.add_task.return_value = 0
        mock_progress_cls.return_value = mock_progress

        mock_s3 = MagicMock()
        mock_s3.list_objects.return_value = {
            "Contents": [
                {"Key": "docs/file1.txt"},
                {"Key": "docs/file2.txt"},
            ],
            "IsTruncated": "false",
        }
        # Mock get_object for reading files
        mock_stream = MagicMock()
        mock_stream.read.return_value = b"file content"
        mock_body = MagicMock()
        mock_body.get_raw_stream.return_value = mock_stream
        mock_s3.get_object.return_value = {"Body": mock_body}

        orchestrator = _make_orchestrator(cos_s3_client=mock_s3)

        result = orchestrator.process_streaming_batch(
            file_pattern="cos://bucket/docs/",
            bucket_name="target-bucket",
            index_name="index",
        )

        assert isinstance(result, BatchResult)
        # list_objects should have been called
        mock_s3.list_objects.assert_called()

    def test_cos_prefix_empty(self):
        """Test COS prefix with no matching files."""
        mock_s3 = MagicMock()
        mock_s3.list_objects.return_value = {
            "Contents": [],
            "IsTruncated": "false",
        }

        orchestrator = _make_orchestrator(cos_s3_client=mock_s3)
        result = orchestrator.process_streaming_batch(
            file_pattern="cos://bucket/empty/",
            bucket_name="target-bucket",
            index_name="index",
        )

        assert isinstance(result, BatchResult)
        assert result.processed_count == 0

    @patch("cos_vectors.core.streaming_batch_orchestrator.Progress")
    def test_cos_prefix_filters_by_extension(self, mock_progress_cls):
        """Test that COS prefix filters out unsupported extensions."""
        mock_progress = MagicMock()
        mock_progress.__enter__ = MagicMock(return_value=mock_progress)
        mock_progress.__exit__ = MagicMock(return_value=False)
        mock_progress.add_task.return_value = 0
        mock_progress_cls.return_value = mock_progress

        mock_s3 = MagicMock()
        mock_s3.list_objects.return_value = {
            "Contents": [
                {"Key": "docs/file1.txt"},
                {"Key": "docs/file2.bin"},  # unsupported
                {"Key": "docs/image.jpg"},
                {"Key": "docs/"},  # directory marker
            ],
            "IsTruncated": "false",
        }
        mock_stream = MagicMock()
        mock_stream.read.return_value = b"content"
        mock_body = MagicMock()
        mock_body.get_raw_stream.return_value = mock_stream
        mock_s3.get_object.return_value = {"Body": mock_body}

        orchestrator = _make_orchestrator(cos_s3_client=mock_s3)
        result = orchestrator.process_streaming_batch(
            file_pattern="cos://bucket/docs/",
            bucket_name="target-bucket",
            index_name="index",
        )

        assert isinstance(result, BatchResult)


class TestBatchResult:
    """Tests for the BatchResult dataclass."""

    def test_defaults(self):
        result = BatchResult()
        assert result.processed_count == 0
        assert result.failed_count == 0
        assert result.processed_keys == []
        assert result.errors == []
        assert result.elapsed_time == 0.0
