"""COS configuration management for cos-vectors-embed-cli."""

import os
from typing import Optional

from qcloud_cos import CosConfig, CosS3Client

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


def get_domain(domain: Optional[str] = None, region: Optional[str] = None) -> str:
    """Get domain from argument, environment variable, or auto-assemble from region.

    Resolution priority (highest to lowest):
    1. Explicit domain parameter (CLI --domain option)
    2. COS_DOMAIN environment variable
    3. Auto-generated from region: vectors.{region}.coslake.com

    Args:
        domain: Explicit domain value. Falls back to COS_DOMAIN env var.
        region: Region value used to auto-assemble domain as fallback.

    Returns:
        Domain string.

    Raises:
        ValueError: If no domain is available and region is not provided.
    """
    domain = domain or os.environ.get("COS_DOMAIN")
    if not domain:
        if region:
            domain = f"vectors.{region}.coslake.com"
        else:
            raise ValueError(
                "Domain is required. Use --domain option, set COS_DOMAIN environment variable, "
                "or provide --region to auto-generate domain. "
                "Example: vectors.ap-guangzhou.coslake.com"
            )
    return domain


def get_user_agent() -> str:
    """Return the user agent string for this CLI tool."""
    return f"cos-vectors-embed/{__version__}"


def get_cos_s3_config(
    region: str,
    secret_id: Optional[str] = None,
    secret_key: Optional[str] = None,
    token: Optional[str] = None,
) -> CosConfig:
    """Create a CosConfig instance for COS object storage read operations.

    Unlike get_cos_config() which uses Domain for vector service access,
    this function uses Region to build standard COS S3 endpoints for
    get_object / list_objects operations.

    Args:
        region: COS region, e.g. 'ap-guangzhou'.
        secret_id: COS SecretId. Falls back to COS_SECRET_ID env var.
        secret_key: COS SecretKey. Falls back to COS_SECRET_KEY env var.
        token: Temporary token. Falls back to COS_TOKEN env var.

    Returns:
        Configured CosConfig instance for object storage operations.

    Raises:
        ValueError: If required credentials are missing.
    """
    secret_id = secret_id or os.environ.get("COS_SECRET_ID")
    secret_key = secret_key or os.environ.get("COS_SECRET_KEY")
    token = token or os.environ.get("COS_TOKEN")

    if not secret_id or not secret_key:
        raise ValueError(
            "COS credentials are required for object storage access. "
            "Set COS_SECRET_ID and COS_SECRET_KEY environment variables, "
            "or pass them as arguments."
        )

    return CosConfig(
        Region=region,
        SecretId=secret_id,
        SecretKey=secret_key,
        Token=token,
    )


def create_cos_s3_client(region: str) -> CosS3Client:
    """Create a CosS3Client for COS object storage read operations.

    Convenience function that creates a CosConfig via get_cos_s3_config()
    and returns a ready-to-use CosS3Client instance.

    Args:
        region: COS region, e.g. 'ap-guangzhou'.

    Returns:
        CosS3Client instance for get_object / list_objects.

    Raises:
        ValueError: If required credentials are missing.
    """
    config = get_cos_s3_config(region=region)
    return CosS3Client(config)


def init_services(
    provider: str,
    embedding_api_base: Optional[str],
    embedding_api_key: Optional[str],
    model_id: str,
    region: str,
    domain: str,
    text: Optional[str],
    console,
    debug: bool,
):
    """Initialize shared services for put/query commands.

    Validates embedding API config, creates embedding provider,
    COS vector service, and optionally a COS S3 client.

    Args:
        provider: Embedding provider type (e.g. 'openai-compatible').
        embedding_api_base: Embedding API base URL.
        embedding_api_key: Embedding API key.
        model_id: Embedding model ID.
        region: COS region.
        domain: Vectors service domain.
        text: Text input (used to decide if COS S3 client is needed).
        console: Rich Console instance.
        debug: Whether debug mode is enabled.

    Returns:
        Tuple of (embedding_provider, cos_service, cos_s3_client).
        cos_s3_client is None if text is not a COS URI.

    Raises:
        click.UsageError: If embedding API config is missing.
    """
    import click

    from cos_vectors.core.cos_vector_service import COSVectorService
    from cos_vectors.core.embedding_provider import get_provider
    from cos_vectors.utils.multimodal_helpers import is_cos_uri

    if not embedding_api_base:
        raise click.UsageError(
            "Embedding API base URL is required. "
            "Use --embedding-api-base or set EMBEDDING_API_BASE env var."
        )
    if not embedding_api_key:
        raise click.UsageError(
            "Embedding API key is required. "
            "Use --embedding-api-key or set EMBEDDING_API_KEY env var."
        )

    embedding_provider = get_provider(
        provider_type=provider,
        api_base=embedding_api_base,
        api_key=embedding_api_key,
        default_model=model_id,
        console=console,
        debug=debug,
    )

    cos_service = COSVectorService(
        region=region,
        domain=domain,
        debug=debug,
        console=console,
    )

    cos_s3_client = None
    if text and is_cos_uri(text):
        cos_s3_client = create_cos_s3_client(region)
        if debug:
            console.print("[dim]Created COS S3 client for object storage read[/dim]")

    return embedding_provider, cos_service, cos_s3_client
