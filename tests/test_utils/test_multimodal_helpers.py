"""Tests for cos_vectors.utils.multimodal_helpers."""

import base64

import pytest

from cos_vectors.utils.multimodal_helpers import (
    create_source_metadata,
    get_mime_type,
    is_cos_uri,
    is_http_url,
    is_local_path,
    parse_cos_uri,
    read_file_content,
    read_image_as_base64,
)


# ── parse_cos_uri ──────────────────────────────────────────────────

class TestParseCosUri:
    def test_standard_uri(self):
        bucket, key = parse_cos_uri("cos://mybucket/path/to/file.txt")
        assert bucket == "mybucket"
        assert key == "path/to/file.txt"

    def test_root_key(self):
        bucket, key = parse_cos_uri("cos://mybucket/file.txt")
        assert bucket == "mybucket"
        assert key == "file.txt"

    def test_deep_nested_key(self):
        bucket, key = parse_cos_uri("cos://mybucket/a/b/c/d/file.txt")
        assert bucket == "mybucket"
        assert key == "a/b/c/d/file.txt"

    def test_invalid_uri_https(self):
        with pytest.raises(ValueError, match="Invalid COS URI"):
            parse_cos_uri("https://example.com/file.txt")

    def test_invalid_uri_no_key(self):
        with pytest.raises(ValueError, match="Invalid COS URI"):
            parse_cos_uri("cos://mybucket/")

    def test_invalid_uri_no_bucket(self):
        with pytest.raises(ValueError, match="Invalid COS URI"):
            parse_cos_uri("cos:///key")

    def test_invalid_uri_local_path(self):
        with pytest.raises(ValueError, match="Invalid COS URI"):
            parse_cos_uri("/local/path/file.txt")


# ── Type Detection ─────────────────────────────────────────────────

class TestIsCosUri:
    def test_true(self):
        assert is_cos_uri("cos://bucket/key") is True

    def test_false_local(self):
        assert is_cos_uri("/local/path/file.txt") is False

    def test_false_http(self):
        assert is_cos_uri("https://example.com") is False


class TestIsHttpUrl:
    def test_https(self):
        assert is_http_url("https://example.com/doc.txt") is True

    def test_http(self):
        assert is_http_url("http://example.com/doc.txt") is True

    def test_false_cos(self):
        assert is_http_url("cos://bucket/key") is False

    def test_false_local(self):
        assert is_http_url("/local/path") is False


class TestIsLocalPath:
    def test_absolute_path(self):
        assert is_local_path("/home/user/file.txt") is True

    def test_relative_path(self):
        assert is_local_path("relative/path.txt") is True

    def test_false_cos(self):
        assert is_local_path("cos://bucket/key") is False

    def test_false_http(self):
        assert is_local_path("https://example.com") is False


# ── File I/O ───────────────────────────────────────────────────────

class TestReadFileContent:
    def test_read_existing_file(self, tmp_text_file):
        content = read_file_content(tmp_text_file)
        assert content == "test content"

    def test_read_nonexistent_file(self):
        with pytest.raises(FileNotFoundError):
            read_file_content("/nonexistent/path.txt")


class TestReadImageAsBase64:
    def test_read_existing_image(self, tmp_image_file):
        result = read_image_as_base64(tmp_image_file)
        assert isinstance(result, str)
        assert len(result) > 0
        # Verify it's valid base64
        decoded = base64.b64decode(result)
        assert len(decoded) > 0

    def test_read_nonexistent_image(self):
        with pytest.raises(FileNotFoundError):
            read_image_as_base64("/nonexistent/image.png")


# ── get_mime_type ──────────────────────────────────────────────────

class TestGetMimeType:
    def test_jpeg(self):
        assert get_mime_type("photo.jpg") == "image/jpeg"

    def test_png(self):
        assert get_mime_type("image.png") == "image/png"

    def test_text(self):
        assert get_mime_type("document.txt") == "text/plain"

    def test_unknown(self):
        assert get_mime_type("file.zzzzunknown") == "application/octet-stream"


# ── create_source_metadata ─────────────────────────────────────────

class TestCreateSourceMetadata:
    def test_with_source_location(self):
        meta = create_source_metadata("text", "/path/to/file.txt")
        assert meta["COSVECTORS-EMBED-SRC-TYPE"] == "text"
        assert meta["COSVECTORS-EMBED-SRC-LOCATION"] == "/path/to/file.txt"

    def test_without_source_location(self):
        meta = create_source_metadata("image")
        assert meta["COSVECTORS-EMBED-SRC-TYPE"] == "image"
        assert "COSVECTORS-EMBED-SRC-LOCATION" not in meta

    def test_video_type(self):
        meta = create_source_metadata("video", "cos://bucket/video.mp4")
        assert meta["COSVECTORS-EMBED-SRC-TYPE"] == "video"
