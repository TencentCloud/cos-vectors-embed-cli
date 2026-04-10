"""Tests for cos_vectors.commands.embed_query."""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from cos_vectors.cli import cli


class TestEmbedQueryCLI:
    """CLI integration tests using CliRunner."""

    def test_missing_vector_bucket_name(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["query", "--index-name", "idx", "--model-id", "m"])
        assert result.exit_code != 0

    def test_missing_index_name(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["query", "--vector-bucket-name", "b", "--model-id", "m"])
        assert result.exit_code != 0

    def test_missing_model_id(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["query", "--vector-bucket-name", "b", "--index-name", "i"])
        assert result.exit_code != 0

    @patch.dict("os.environ", {
        "COS_REGION": "ap-guangzhou",
        "COS_DOMAIN": "vectors.test.com",
        "COS_SECRET_ID": "test-id",
        "COS_SECRET_KEY": "test-key",
    })
    def test_no_query_input(self):
        runner = CliRunner()
        result = runner.invoke(cli, [
            "query",
            "--vector-bucket-name", "b",
            "--index-name", "i",
            "--model-id", "m",
            "--embedding-api-base", "http://localhost",
            "--embedding-api-key", "key",
        ])
        assert result.exit_code != 0
        assert "query input" in result.output.lower() or "input is required" in result.output.lower()

    @patch("cos_vectors.core.embedding_provider.get_provider")
    @patch("cos_vectors.core.cos_vector_service.COSVectorService")
    @patch.dict("os.environ", {
        "COS_REGION": "ap-guangzhou",
        "COS_DOMAIN": "vectors.test.com",
        "COS_SECRET_ID": "test-id",
        "COS_SECRET_KEY": "test-key",
    })
    def test_successful_text_query(self, mock_cos_service_cls, mock_get_provider):
        # Mock embedding provider
        mock_provider = MagicMock()
        mock_provider.embed_texts.return_value = [[0.1, 0.2, 0.3]]
        mock_get_provider.return_value = mock_provider

        # Mock COS service
        mock_service = MagicMock()
        mock_service.query_vectors.return_value = [
            {"key": "result-1", "distance": 0.1, "metadata": {"type": "text"}}
        ]
        mock_cos_service_cls.return_value = mock_service

        runner = CliRunner()
        result = runner.invoke(cli, [
            "query",
            "--vector-bucket-name", "b",
            "--index-name", "i",
            "--model-id", "m",
            "--embedding-api-base", "http://localhost",
            "--embedding-api-key", "key",
            "--text-value", "search query",
        ])

        assert result.exit_code == 0

    @patch("cos_vectors.core.embedding_provider.get_provider")
    @patch("cos_vectors.core.cos_vector_service.COSVectorService")
    @patch.dict("os.environ", {
        "COS_REGION": "ap-guangzhou",
        "COS_DOMAIN": "vectors.test.com",
        "COS_SECRET_ID": "test-id",
        "COS_SECRET_KEY": "test-key",
    })
    def test_query_with_json_filter(self, mock_cos_service_cls, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.embed_texts.return_value = [[0.1, 0.2]]
        mock_get_provider.return_value = mock_provider

        mock_service = MagicMock()
        mock_service.query_vectors.return_value = []
        mock_cos_service_cls.return_value = mock_service

        runner = CliRunner()
        result = runner.invoke(cli, [
            "query",
            "--vector-bucket-name", "b",
            "--index-name", "i",
            "--model-id", "m",
            "--embedding-api-base", "http://localhost",
            "--embedding-api-key", "key",
            "--text-value", "test",
            "--filter", '{"category": {"$eq": "finance"}}',
        ])

        assert result.exit_code == 0
        mock_service.query_vectors.assert_called_once()
        call_kwargs = mock_service.query_vectors.call_args[1]
        assert call_kwargs["filter_expr"] == {"category": {"$eq": "finance"}}

    @patch("cos_vectors.core.embedding_provider.get_provider")
    @patch("cos_vectors.core.cos_vector_service.COSVectorService")
    @patch.dict("os.environ", {
        "COS_REGION": "ap-guangzhou",
        "COS_DOMAIN": "vectors.test.com",
        "COS_SECRET_ID": "test-id",
        "COS_SECRET_KEY": "test-key",
    })
    def test_query_with_complex_nested_filter(self, mock_cos_service_cls, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.embed_texts.return_value = [[0.1, 0.2]]
        mock_get_provider.return_value = mock_provider

        mock_service = MagicMock()
        mock_service.query_vectors.return_value = []
        mock_cos_service_cls.return_value = mock_service

        complex_filter = '{"$and": [{"category": {"$eq": "finance"}}, {"year": {"$gte": 2020}}]}'
        runner = CliRunner()
        result = runner.invoke(cli, [
            "query",
            "--vector-bucket-name", "b",
            "--index-name", "i",
            "--model-id", "m",
            "--embedding-api-base", "http://localhost",
            "--embedding-api-key", "key",
            "--text-value", "test",
            "--filter", complex_filter,
        ])

        assert result.exit_code == 0
        call_kwargs = mock_service.query_vectors.call_args[1]
        assert call_kwargs["filter_expr"] == {
            "$and": [
                {"category": {"$eq": "finance"}},
                {"year": {"$gte": 2020}},
            ]
        }

    @patch.dict("os.environ", {
        "COS_REGION": "ap-guangzhou",
        "COS_DOMAIN": "vectors.test.com",
        "COS_SECRET_ID": "test-id",
        "COS_SECRET_KEY": "test-key",
    })
    def test_query_with_invalid_filter_json(self):
        runner = CliRunner()
        result = runner.invoke(cli, [
            "query",
            "--vector-bucket-name", "b",
            "--index-name", "i",
            "--model-id", "m",
            "--embedding-api-base", "http://localhost",
            "--embedding-api-key", "key",
            "--text-value", "test",
            "--filter", 'category = "finance"',
        ])

        assert result.exit_code != 0
        assert "Invalid --filter JSON" in result.output

    @patch("cos_vectors.core.embedding_provider.get_provider")
    @patch("cos_vectors.core.cos_vector_service.COSVectorService")
    @patch.dict("os.environ", {
        "COS_REGION": "ap-guangzhou",
        "COS_DOMAIN": "vectors.test.com",
        "COS_SECRET_ID": "test-id",
        "COS_SECRET_KEY": "test-key",
    })
    def test_query_without_filter(self, mock_cos_service_cls, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.embed_texts.return_value = [[0.1, 0.2]]
        mock_get_provider.return_value = mock_provider

        mock_service = MagicMock()
        mock_service.query_vectors.return_value = []
        mock_cos_service_cls.return_value = mock_service

        runner = CliRunner()
        result = runner.invoke(cli, [
            "query",
            "--vector-bucket-name", "b",
            "--index-name", "i",
            "--model-id", "m",
            "--embedding-api-base", "http://localhost",
            "--embedding-api-key", "key",
            "--text-value", "test",
        ])

        assert result.exit_code == 0
        call_kwargs = mock_service.query_vectors.call_args[1]
        assert call_kwargs["filter_expr"] is None

    @patch("cos_vectors.core.embedding_provider.get_provider")
    @patch("cos_vectors.core.cos_vector_service.COSVectorService")
    @patch.dict("os.environ", {
        "COS_REGION": "ap-guangzhou",
        "COS_DOMAIN": "vectors.test.com",
        "COS_SECRET_ID": "test-id",
        "COS_SECRET_KEY": "test-key",
    })
    def test_query_table_output(self, mock_cos_service_cls, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.embed_texts.return_value = [[0.1, 0.2]]
        mock_get_provider.return_value = mock_provider

        mock_service = MagicMock()
        mock_service.query_vectors.return_value = {
            "vectors": [{"key": "r1", "distance": 0.5, "metadata": {}}]
        }
        mock_cos_service_cls.return_value = mock_service

        runner = CliRunner()
        result = runner.invoke(cli, [
            "query",
            "--vector-bucket-name", "b",
            "--index-name", "i",
            "--model-id", "m",
            "--embedding-api-base", "http://localhost",
            "--embedding-api-key", "key",
            "--text-value", "test",
            "--output", "table",
        ])

        assert result.exit_code == 0
