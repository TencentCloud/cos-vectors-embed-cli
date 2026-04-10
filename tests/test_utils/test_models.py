"""Tests for cos_vectors.utils.models."""

import uuid

import pytest

from cos_vectors.utils.models import (
    ProcessingInput,
    detect_content_type_from_extension,
    determine_content_type,
    extract_key_from_source,
    generate_vector_key,
    prepare_processing_input,
)


# ── determine_content_type ─────────────────────────────────────────

class TestDetermineContentType:
    def test_text_value(self):
        assert determine_content_type(text_value="hello") == "text"

    def test_text_file(self):
        assert determine_content_type(text="doc.txt") == "text"

    def test_image(self):
        assert determine_content_type(image="photo.jpg") == "image"

    def test_video(self):
        assert determine_content_type(video="clip.mp4") == "video"

    def test_text_value_priority_over_image(self):
        assert determine_content_type(text_value="hello", image="photo.jpg") == "text"

    def test_no_input_raises(self):
        with pytest.raises(ValueError, match="No input provided"):
            determine_content_type()

    def test_all_none(self):
        with pytest.raises(ValueError):
            determine_content_type(
                text_value=None, text=None, image=None, video=None
            )


# ── prepare_processing_input ───────────────────────────────────────

class TestPrepareProcessingInput:
    def test_text_value_input(self):
        result = prepare_processing_input(text_value="hello world")
        assert isinstance(result, ProcessingInput)
        assert result.content_type == "text"
        assert result.data == "hello world"
        assert result.source_location == "inline"

    def test_text_file_input(self):
        result = prepare_processing_input(text="/path/to/doc.txt")
        assert result.content_type == "text"
        assert result.data is None  # Data loaded later
        assert result.source_location == "/path/to/doc.txt"

    def test_image_input(self):
        result = prepare_processing_input(image="photo.jpg")
        assert result.content_type == "image"
        assert result.source_location == "photo.jpg"

    def test_metadata_default(self):
        result = prepare_processing_input(text_value="x")
        assert result.metadata == {}

    def test_custom_metadata(self):
        meta = {"category": "finance"}
        result = prepare_processing_input(text_value="x", metadata=meta)
        assert result.metadata == meta

    def test_custom_key(self):
        result = prepare_processing_input(text_value="x", custom_key="my-key")
        assert result.custom_key == "my-key"


# ── generate_vector_key ────────────────────────────────────────────

class TestGenerateVectorKey:
    def test_custom_key(self):
        assert generate_vector_key(custom_key="my-key") == "my-key"

    def test_custom_key_with_prefix(self):
        assert generate_vector_key(custom_key="my-key", key_prefix="prefix/") == "prefix/my-key"

    def test_filename_as_key(self):
        key = generate_vector_key(
            filename_as_key=True,
            source_location="/path/to/doc.txt",
        )
        assert key == "doc.txt"

    def test_filename_as_key_with_prefix(self):
        key = generate_vector_key(
            filename_as_key=True,
            source_location="/path/to/doc.txt",
            key_prefix="prefix/",
        )
        assert key == "prefix/doc.txt"

    def test_uuid_key(self):
        key = generate_vector_key()
        # Should be a valid UUID
        uuid.UUID(key)

    def test_uuid_key_with_prefix(self):
        key = generate_vector_key(key_prefix="test/")
        assert key.startswith("test/")
        # The rest should be a valid UUID
        uuid.UUID(key[5:])


# ── extract_key_from_source ────────────────────────────────────────

class TestExtractKeyFromSource:
    def test_local_path(self):
        assert extract_key_from_source("/path/to/document.txt") == "document.txt"

    def test_cos_uri(self):
        assert extract_key_from_source("cos://bucket/path/to/file.txt") == "file.txt"

    def test_http_url(self):
        assert extract_key_from_source("https://example.com/path/doc.txt") == "doc.txt"

    def test_cos_uri_root(self):
        assert extract_key_from_source("cos://bucket/file.txt") == "file.txt"


# ── detect_content_type_from_extension ─────────────────────────────

class TestDetectContentTypeFromExtension:
    def test_text_txt(self):
        assert detect_content_type_from_extension("document.txt") == "text"

    def test_text_md(self):
        assert detect_content_type_from_extension("readme.md") == "text"

    def test_text_py(self):
        assert detect_content_type_from_extension("script.py") == "text"

    def test_image_jpg(self):
        assert detect_content_type_from_extension("photo.jpg") == "image"

    def test_image_png(self):
        assert detect_content_type_from_extension("image.png") == "image"

    def test_video_mp4(self):
        assert detect_content_type_from_extension("clip.mp4") == "video"

    def test_unknown_defaults_to_text(self):
        # Source code says "Default to text for unknown extensions"
        assert detect_content_type_from_extension("file.xyz") == "text"

    def test_no_extension_defaults_to_text(self):
        assert detect_content_type_from_extension("README") == "text"
