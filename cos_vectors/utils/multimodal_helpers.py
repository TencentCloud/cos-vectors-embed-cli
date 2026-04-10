"""Multimodal helpers for cos-vectors-embed."""

import base64
import mimetypes
import os
from typing import Any, Dict, Optional, Tuple


def parse_cos_uri(uri: str) -> Tuple[str, str]:
    """Parse a COS URI into (bucket, key) tuple.

    Args:
        uri: COS URI in format cos://bucket/key.

    Returns:
        Tuple of (bucket_name, object_key).

    Raises:
        ValueError: If the URI is not a valid cos:// URI.
    """
    if not uri.startswith("cos://"):
        raise ValueError(
            f"Invalid COS URI: '{uri}'. Expected format: cos://bucket/key"
        )

    # Remove the cos:// prefix
    path = uri[6:]  # len("cos://") == 6
    parts = path.split("/", 1)

    if len(parts) < 2 or not parts[0] or not parts[1]:
        raise ValueError(
            f"Invalid COS URI: '{uri}'. Expected format: cos://bucket/key"
        )

    return parts[0], parts[1]


def is_cos_uri(path: str) -> bool:
    """Check if a path is a COS URI.

    Args:
        path: Path string to check.

    Returns:
        True if path starts with cos://.
    """
    return path.startswith("cos://")


def is_http_url(path: str) -> bool:
    """Check if a path is an HTTP/HTTPS URL.

    Args:
        path: Path string to check.

    Returns:
        True if path starts with http:// or https://.
    """
    return path.startswith(("http://", "https://"))


def is_local_path(path: str) -> bool:
    """Check if a path is a local file path.

    Args:
        path: Path string to check.

    Returns:
        True if path is not a COS URI or HTTP URL.
    """
    return not is_cos_uri(path) and not is_http_url(path)


def read_file_content(filepath: str) -> str:
    """Read text content from a local file path.

    Args:
        filepath: Local file path.

    Returns:
        File text content.

    Raises:
        FileNotFoundError: If file does not exist.
        IOError: If file cannot be read.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def read_file_content_from_url(url: str) -> str:
    """Read text content from an HTTP/HTTPS URL.

    Args:
        url: HTTP/HTTPS URL.

    Returns:
        Downloaded text content.

    Raises:
        RuntimeError: If download fails.
    """
    import urllib.request

    try:
        with urllib.request.urlopen(url) as response:
            return response.read().decode("utf-8")
    except Exception as e:
        raise RuntimeError(f"Failed to download content from {url}: {e}") from e


def read_image_as_base64(filepath: str) -> str:
    """Read a local image file and return base64-encoded string.

    Args:
        filepath: Local image file path.

    Returns:
        Base64-encoded string of the image content.

    Raises:
        FileNotFoundError: If file does not exist.
        IOError: If file cannot be read.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Image file not found: {filepath}")

    with open(filepath, "rb") as f:
        content = f.read()

    return base64.b64encode(content).decode("utf-8")


def get_mime_type(filepath: str) -> str:
    """Detect MIME type from a file path.

    Args:
        filepath: File path or name.

    Returns:
        MIME type string (e.g. 'image/jpeg', 'text/plain').
    """
    mime_type, _ = mimetypes.guess_type(filepath)
    return mime_type or "application/octet-stream"


def create_source_metadata(
    content_type: str,
    source_location: Optional[str] = None,
) -> Dict[str, Any]:
    """Create standard source metadata with COSVECTORS-EMBED-SRC-* prefix.

    Args:
        content_type: Content type ('text', 'image', 'video').
        source_location: Source file path or URI.

    Returns:
        Metadata dict with standardized keys.
    """
    metadata: Dict[str, Any] = {}

    if source_location:
        metadata["COSVECTORS-EMBED-SRC-LOCATION"] = source_location

    metadata["COSVECTORS-EMBED-SRC-TYPE"] = content_type

    return metadata
