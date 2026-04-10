"""Tests for cos_vectors.commands.embed_put."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cos_vectors.cli import cli
from cos_vectors.commands.embed_put import (
    _has_glob_pattern,
    _is_cos_prefix,
    _needs_batch_mode,
    _validate_inputs,
)


# ── Helper Functions ───────────────────────────────────────────────

class TestHasGlobPattern:
    def test_star(self):
        assert _has_glob_pattern("docs/*.txt") is True

    def test_question_mark(self):
        assert _has_glob_pattern("doc?.txt") is True

    def test_bracket(self):
        assert _has_glob_pattern("doc[0-9].txt") is True

    def test_plain_path(self):
        assert _has_glob_pattern("/path/to/file.txt") is False

    def test_cos_uri_no_glob(self):
        assert _has_glob_pattern("cos://bucket/file.txt") is False


class TestIsCosPrefix:
    def test_cos_wildcard(self):
        assert _is_cos_prefix("cos://bucket/docs/*") is True

    def test_cos_trailing_slash(self):
        assert _is_cos_prefix("cos://bucket/docs/") is True

    def test_cos_single_file(self):
        assert _is_cos_prefix("cos://bucket/single-file.txt") is False

    def test_local_path(self):
        assert _is_cos_prefix("/path/to/docs/") is False


class TestNeedsBatchMode:
    def test_glob(self):
        assert _needs_batch_mode("docs/*.txt") is True

    def test_cos_prefix(self):
        assert _needs_batch_mode("cos://bucket/docs/") is True

    def test_single_file(self):
        assert _needs_batch_mode("/path/to/file.txt") is False

    def test_cos_single_file(self):
        assert _needs_batch_mode("cos://bucket/file.txt") is False


class TestValidateInputs:
    def test_no_inputs_raises(self):
        with pytest.raises(Exception):
            _validate_inputs(None, None, None)

    def test_text_value_ok(self):
        _validate_inputs("hello", None, None)  # Should not raise

    def test_text_ok(self):
        _validate_inputs(None, "file.txt", None)  # Should not raise

    def test_video_ok(self):
        _validate_inputs(None, None, "video.mp4")  # Should not raise


# ── CLI Tests ──────────────────────────────────────────────────────

class TestEmbedPutCLI:
    """CLI integration tests using CliRunner."""

    def test_missing_vector_bucket_name(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["put", "--index-name", "idx", "--model-id", "m"])
        assert result.exit_code != 0
        assert "vector-bucket-name" in result.output.lower() or result.exit_code == 2

    def test_missing_index_name(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["put", "--vector-bucket-name", "b", "--model-id", "m"])
        assert result.exit_code != 0

    def test_missing_model_id(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["put", "--vector-bucket-name", "b", "--index-name", "i"])
        assert result.exit_code != 0

    @patch.dict("os.environ", {
        "COS_REGION": "ap-guangzhou",
        "COS_DOMAIN": "vectors.test.com",
        "COS_SECRET_ID": "test-id",
        "COS_SECRET_KEY": "test-key",
    })
    def test_no_input_source(self):
        runner = CliRunner()
        result = runner.invoke(cli, [
            "put",
            "--vector-bucket-name", "b",
            "--index-name", "i",
            "--model-id", "m",
            "--embedding-api-base", "http://localhost",
            "--embedding-api-key", "key",
        ])
        assert result.exit_code != 0
        assert "at least one input" in result.output.lower() or "input is required" in result.output.lower()

    @patch.dict("os.environ", {
        "COS_REGION": "ap-guangzhou",
        "COS_DOMAIN": "vectors.test.com",
        "COS_SECRET_ID": "test-id",
        "COS_SECRET_KEY": "test-key",
    })
    def test_missing_api_base(self):
        runner = CliRunner()
        result = runner.invoke(cli, [
            "put",
            "--vector-bucket-name", "b",
            "--index-name", "i",
            "--model-id", "m",
            "--text-value", "hello",
        ])
        assert result.exit_code != 0
        assert "api base" in result.output.lower() or "embedding" in result.output.lower()

    @patch("cos_vectors.core.embedding_provider.get_provider")
    @patch("cos_vectors.core.cos_vector_service.COSVectorService")
    @patch.dict("os.environ", {
        "COS_REGION": "ap-guangzhou",
        "COS_DOMAIN": "vectors.test.com",
        "COS_SECRET_ID": "test-id",
        "COS_SECRET_KEY": "test-key",
    })
    def test_successful_text_value_put(self, mock_cos_service_cls, mock_get_provider):
        # Mock embedding provider
        mock_provider = MagicMock()
        mock_provider.embed_texts.return_value = [[0.1, 0.2, 0.3]]
        mock_get_provider.return_value = mock_provider

        # Mock COS service
        mock_service = MagicMock()
        mock_service.get_index.return_value = {"dimension": 3}
        mock_service.put_vectors_batch.return_value = ["test-key"]
        mock_cos_service_cls.return_value = mock_service

        runner = CliRunner()
        result = runner.invoke(cli, [
            "put",
            "--vector-bucket-name", "b",
            "--index-name", "i",
            "--model-id", "m",
            "--embedding-api-base", "http://localhost",
            "--embedding-api-key", "key",
            "--text-value", "hello world",
        ])

        assert result.exit_code == 0
