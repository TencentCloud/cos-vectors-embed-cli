"""Shared test fixtures for cos-vectors-embed tests."""

import os
import tempfile
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_embedding_provider():
    """Mock EmbeddingProvider that returns fixed-dimension vectors."""
    provider = MagicMock()
    provider.embed_texts.return_value = [[0.1, 0.2, 0.3]]
    provider.embed_image.return_value = [0.4, 0.5, 0.6]
    return provider


@pytest.fixture
def mock_cos_service():
    """Mock COSVectorService that does not call real COS API."""
    service = MagicMock()
    service.put_vectors_batch.return_value = ["test-key-1"]
    service.query_vectors.return_value = [
        {"key": "result-1", "distance": 0.1, "metadata": {"type": "text"}}
    ]
    service.get_index.return_value = {"dimension": 3, "metric": "cosine"}
    return service


@pytest.fixture
def mock_console():
    """Silent Rich Console mock."""
    console = MagicMock()
    return console


@pytest.fixture
def mock_cos_s3_client():
    """Mock CosS3Client that does not call real COS S3 API."""
    client = MagicMock()
    # Default: return text content
    mock_stream = MagicMock()
    mock_stream.read.return_value = b"mock cos content"
    mock_body = MagicMock()
    mock_body.get_raw_stream.return_value = mock_stream
    client.get_object.return_value = {"Body": mock_body}
    client.list_objects.return_value = {
        "Contents": [],
        "IsTruncated": "false",
    }
    return client


@pytest.fixture
def tmp_text_file():
    """Temporary text file containing 'test content'."""
    fd, path = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("test content")
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def tmp_image_file():
    """Temporary image file (minimal PNG bytes)."""
    # Minimal valid 1x1 white PNG
    png_bytes = (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx"
        b"\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00"
        b"\x00\x00\x00IEND\xaeB`\x82"
    )
    fd, path = tempfile.mkstemp(suffix=".png")
    with os.fdopen(fd, "wb") as f:
        f.write(png_bytes)
    yield path
    if os.path.exists(path):
        os.unlink(path)
