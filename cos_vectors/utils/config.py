"""COS configuration management for cos-vectors-embed-cli."""

import os
from typing import Optional

from qcloud_cos import CosConfig

from cos_vectors.__version__ import __version__


def get_cos_config(
    region: str,
    domain: str,
    secret_id: Optional[str] = None,
    secret_key: Optional[str] = None,
    token: Optional[str] = None,
) -> CosConfig:
    """Create a CosConfig instance for COS Vectors.

    Uses Domain parameter (not Endpoint) because the vectors API
    does not need {bucket}.{endpoint} URL construction. Domain is
    used directly as the request host.

    Args:
        region: COS region, e.g. 'ap-guangzhou'.
        domain: Vectors service domain, e.g. 'vectors.ap-guangzhou.coslake.com'.
        secret_id: COS SecretId. Falls back to COS_SECRET_ID env var.
        secret_key: COS SecretKey. Falls back to COS_SECRET_KEY env var.
        token: Temporary token. Falls back to COS_TOKEN env var.

    Returns:
        Configured CosConfig instance.

    Raises:
        ValueError: If required credentials are missing.
    """
    secret_id = secret_id or os.environ.get("COS_SECRET_ID")
    secret_key = secret_key or os.environ.get("COS_SECRET_KEY")
    token = token or os.environ.get("COS_TOKEN")

    if not secret_id or not secret_key:
        raise ValueError(
            "COS credentials are required. Set COS_SECRET_ID and COS_SECRET_KEY "
            "environment variables, or pass them as arguments."
        )

    config = CosConfig(
        Region=region,
        SecretId=secret_id,
        SecretKey=secret_key,
        Token=token,
        Domain=domain,
    )
    return config


def get_region(region: Optional[str] = None) -> str:
    """Get region from argument or environment variable.

    Args:
        region: Explicit region value. Falls back to COS_REGION env var.

    Returns:
        Region string.

    Raises:
        ValueError: If no region is available.
    """
    region = region or os.environ.get("COS_REGION")
    if not region:
        raise ValueError(
            "Region is required. Use --region option or set COS_REGION environment variable."
        )
    return region


def get_domain(domain: Optional[str] = None) -> str:
    """Get domain from argument or environment variable.

    Args:
        domain: Explicit domain value. Falls back to COS_DOMAIN env var.

    Returns:
        Domain string.

    Raises:
        ValueError: If no domain is available.
    """
    domain = domain or os.environ.get("COS_DOMAIN")
    if not domain:
        raise ValueError(
            "Domain is required. Use --domain option or set COS_DOMAIN environment variable. "
            "Example: vectors.ap-guangzhou.coslake.com"
        )
    return domain


def get_user_agent() -> str:
    """Return the user agent string for this CLI tool."""
    return f"cos-vectors-embed-cli/{__version__}"
