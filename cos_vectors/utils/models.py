"""Data models and utility functions for cos-vectors-embed-cli."""

import os
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ProcessingInput:
    """Unified processing input structure.

    Attributes:
        content_type: Type of content - 'text', 'image', or 'video'.
        data: Raw content data (text string, base64 image, etc.).
        source_location: Source path/URI of the content.
        metadata: User-defined metadata dict.
        custom_key: Custom vector key (if user-specified).
        filename_as_key: Whether to use source filename as vector key.
        key_prefix: Prefix for generated vector keys.
    """

    content_type: str  # 'text', 'image', 'video'
    data: Any = None
    source_location: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)
    custom_key: Optional[str] = None
    filename_as_key: bool = False
    key_prefix: Optional[str] = None


def determine_content_type(
    text_value: Optional[str] = None,
    text: Optional[str] = None,
    image: Optional[str] = None,
    video: Optional[str] = None,
) -> str:
    """Determine content type from CLI parameters.

    Args:
        text_value: Direct text string input.
        text: Text file path.
        image: Image file path.
        video: Video file path.

    Returns:
        Content type string: 'text', 'image', or 'video'.

    Raises:
        ValueError: If no valid input is provided.
    """
    if text_value or text:
        return "text"
    if image:
        return "image"
    if video:
        return "video"
    raise ValueError(
        "No input provided. Use --text-value, --text, --image, or --video."
    )


def prepare_processing_input(
    text_value: Optional[str] = None,
    text: Optional[str] = None,
    image: Optional[str] = None,
    video: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    custom_key: Optional[str] = None,
    filename_as_key: bool = False,
    key_prefix: Optional[str] = None,
) -> ProcessingInput:
    """Prepare a unified ProcessingInput from CLI arguments.

    Args:
        text_value: Direct text string.
        text: Text file path.
        image: Image file path.
        video: Video file path.
        metadata: User metadata dict.
        custom_key: Custom vector key.
        filename_as_key: Use filename as key flag.
        key_prefix: Key prefix string.

    Returns:
        ProcessingInput instance.
    """
    content_type = determine_content_type(text_value, text, image, video)
    source_location = None
    data = None

    if text_value:
        data = text_value
        source_location = "inline"
    elif text:
        source_location = text
        # Data will be loaded by multimodal_helpers.read_file_content()
    elif image:
        source_location = image
        # Data will be loaded by multimodal_helpers.read_image_as_base64()
    elif video:
        source_location = video

    return ProcessingInput(
        content_type=content_type,
        data=data,
        source_location=source_location,
        metadata=metadata or {},
        custom_key=custom_key,
        filename_as_key=filename_as_key,
        key_prefix=key_prefix,
    )


def generate_vector_key(
    custom_key: Optional[str] = None,
    filename_as_key: bool = False,
    source_location: Optional[str] = None,
    key_prefix: Optional[str] = None,
) -> str:
    """Generate a vector key using the specified strategy.

    Priority:
    1. custom_key - use directly
    2. filename_as_key - extract filename from source_location
    3. UUID auto-generation (default)

    An optional key_prefix is prepended in all cases.

    Args:
        custom_key: User-specified exact key.
        filename_as_key: Use source filename as key.
        source_location: Source file path/URI.
        key_prefix: Optional key prefix.

    Returns:
        Generated vector key string.
    """
    if custom_key:
        key = custom_key
    elif filename_as_key and source_location:
        key = extract_key_from_source(source_location)
    else:
        key = str(uuid.uuid4())

    if key_prefix:
        key = f"{key_prefix}{key}"

    return key


def extract_key_from_source(source_location: str) -> str:
    """Extract a filename-based key from a source path or URI.

    Supports local paths, COS URIs (cos://bucket/key), and HTTP URLs.

    Args:
        source_location: Source path or URI string.

    Returns:
        Extracted filename or last path component.
    """
    if source_location.startswith("cos://"):
        # cos://bucket/path/to/file.txt -> file.txt
        path = source_location.split("//", 1)[1]
        parts = path.split("/")
        return parts[-1] if len(parts) > 1 else parts[0]
    elif source_location.startswith(("http://", "https://")):
        # https://example.com/path/to/file.txt -> file.txt
        from urllib.parse import urlparse

        parsed = urlparse(source_location)
        return os.path.basename(parsed.path) or str(uuid.uuid4())
    else:
        # Local path
        return os.path.basename(source_location)


# Common image extensions
IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif", ".svg",
}

# Common text extensions
TEXT_EXTENSIONS = {
    ".txt", ".md", ".csv", ".json", ".xml", ".html", ".htm", ".yaml", ".yml",
    ".log", ".cfg", ".ini", ".conf", ".py", ".js", ".ts", ".java", ".c",
    ".cpp", ".h", ".go", ".rs", ".rb", ".php", ".sh", ".bash",
}

# Common video extensions
VIDEO_EXTENSIONS = {
    ".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv", ".webm", ".m4v",
}


def detect_content_type_from_extension(filepath: str) -> str:
    """Detect content type from file extension.

    Args:
        filepath: File path or name.

    Returns:
        Content type: 'text', 'image', or 'video'.
    """
    ext = os.path.splitext(filepath)[1].lower()
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in VIDEO_EXTENSIONS:
        return "video"
    # Default to text for unknown extensions
    return "text"
