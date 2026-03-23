"""Put subcommand for cos-vectors-embed-cli.

Vectorizes content and writes to COS Vector index.
"""

import glob
import json
from typing import Any, Dict, Optional

import click
from rich.console import Console
from rich.json import JSON as RichJSON
from rich.table import Table

from cos_vectors.core.cos_vector_service import COSVectorService
from cos_vectors.core.embedding_provider import get_provider
from cos_vectors.core.streaming_batch_orchestrator import StreamingBatchOrchestrator
from cos_vectors.core.unified_processor import UnifiedProcessor
from cos_vectors.utils.config import get_domain, get_region
from cos_vectors.utils.models import prepare_processing_input


def _has_glob_pattern(path: str) -> bool:
    """Check if a path contains glob wildcard characters."""
    return any(c in path for c in ("*", "?", "["))


def _validate_inputs(text_value, text, image, video):
    """Validate that at least one input source is provided."""
    if not any([text_value, text, image, video]):
        raise click.UsageError(
            "At least one input is required: "
            "--text-value, --text, --image, or --video"
        )


@click.command()
@click.option(
    "--vector-bucket-name",
    required=True,
    help="COS vector bucket name.",
)
@click.option(
    "--index-name",
    required=True,
    help="Vector index name.",
)
@click.option(
    "--model-id",
    required=True,
    help="Embedding model identifier.",
)
@click.option(
    "--text-value",
    default=None,
    help="Direct text string to embed.",
)
@click.option(
    "--text",
    default=None,
    help="Local text file path (supports glob patterns).",
)
@click.option(
    "--image",
    default=None,
    help="Local image file path (supports glob patterns).",
)
@click.option(
    "--video",
    default=None,
    help="Local video file path (reserved for future use).",
)
@click.option(
    "--key",
    default=None,
    help="Custom vector key. Only for single-item puts.",
)
@click.option(
    "--key-prefix",
    default=None,
    help="Prefix for generated vector keys.",
)
@click.option(
    "--filename-as-key",
    is_flag=True,
    default=False,
    help="Use source filename as vector key.",
)
@click.option(
    "--metadata",
    default=None,
    help='Custom metadata as JSON string, e.g. \'{"category": "finance"}\'.',
)
@click.option(
    "--provider",
    default="openai-compatible",
    help="Embedding provider type. Default: openai-compatible.",
)
@click.option(
    "--embedding-api-base",
    default=None,
    envvar="EMBEDDING_API_BASE",
    help="Embedding API base URL. Falls back to EMBEDDING_API_BASE env var.",
)
@click.option(
    "--embedding-api-key",
    default=None,
    envvar="EMBEDDING_API_KEY",
    help="Embedding API key. Falls back to EMBEDDING_API_KEY env var.",
)
@click.option(
    "--embedding-inference-params",
    default=None,
    help="Extra inference parameters as JSON string.",
)
@click.option(
    "--max-workers",
    default=4,
    type=int,
    help="Number of parallel worker threads for batch processing. Default: 4.",
)
@click.option(
    "--batch-size",
    default=100,
    type=int,
    help="Number of items per storage batch. Default: 100.",
)
@click.option(
    "--output",
    type=click.Choice(["json", "table"]),
    default="json",
    help="Output format. Default: json.",
)
@click.option(
    "--region",
    default=None,
    help="Override global --region for this command.",
)
@click.option(
    "--domain",
    default=None,
    help="Override global --domain for this command.",
)
@click.pass_context
def embed_put(
    ctx,
    vector_bucket_name,
    index_name,
    model_id,
    text_value,
    text,
    image,
    video,
    key,
    key_prefix,
    filename_as_key,
    metadata,
    provider,
    embedding_api_base,
    embedding_api_key,
    embedding_inference_params,
    max_workers,
    batch_size,
    output,
    region,
    domain,
):
    """Vectorize content and write to a COS vector index."""
    console: Console = ctx.obj["console"]
    debug: bool = ctx.obj["debug"]

    # Resolve region and domain (command-level overrides global)
    region = get_region(region or ctx.obj.get("region"))
    domain = get_domain(domain or ctx.obj.get("domain"))

    # Validate inputs
    _validate_inputs(text_value, text, image, video)

    # Parse metadata JSON
    user_metadata: Optional[Dict[str, Any]] = None
    if metadata:
        try:
            user_metadata = json.loads(metadata)
        except json.JSONDecodeError as e:
            raise click.UsageError(f"Invalid --metadata JSON: {e}")

    # Parse extra inference params
    extra_params: Optional[Dict[str, Any]] = None
    if embedding_inference_params:
        try:
            extra_params = json.loads(embedding_inference_params)
        except json.JSONDecodeError as e:
            raise click.UsageError(
                f"Invalid --embedding-inference-params JSON: {e}"
            )

    # Validate embedding API config
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

    try:
        # Initialize services
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

        # Detect streaming batch mode (glob patterns)
        file_pattern = text or image
        if file_pattern and _has_glob_pattern(file_pattern):
            # Streaming batch processing
            orchestrator = StreamingBatchOrchestrator(
                embedding_provider=embedding_provider,
                cos_service=cos_service,
                model_id=model_id,
                max_workers=max_workers,
                batch_size=batch_size,
                console=console,
                debug=debug,
            )

            batch_result = orchestrator.process_streaming_batch(
                file_pattern=file_pattern,
                bucket_name=vector_bucket_name,
                index_name=index_name,
                metadata=user_metadata,
                filename_as_key=filename_as_key,
                key_prefix=key_prefix,
            )

            # Display batch results
            if output == "table":
                _display_batch_table(console, batch_result)
            else:
                result_data = {
                    "processed_count": batch_result.processed_count,
                    "failed_count": batch_result.failed_count,
                    "elapsed_time": f"{batch_result.elapsed_time:.2f}s",
                    "keys": batch_result.processed_keys,
                }
                if batch_result.errors:
                    result_data["errors"] = [
                        {"source": src, "error": err}
                        for src, err in batch_result.errors
                    ]
                console.print(RichJSON(json.dumps(result_data, indent=2)))

        else:
            # Single item processing
            processor = UnifiedProcessor(
                embedding_provider=embedding_provider,
                cos_service=cos_service,
                model_id=model_id,
                console=console,
                debug=debug,
            )

            processing_input = prepare_processing_input(
                text_value=text_value,
                text=text,
                image=image,
                video=video,
                metadata=user_metadata,
                custom_key=key,
                filename_as_key=filename_as_key,
                key_prefix=key_prefix,
            )

            result = processor.process(
                processing_input=processing_input,
                bucket_name=vector_bucket_name,
                index_name=index_name,
            )

            written_keys = processor.store_vectors(
                result=result,
                bucket_name=vector_bucket_name,
                index_name=index_name,
            )

            # Display results
            if output == "table":
                _display_put_table(console, written_keys, result)
            else:
                result_data = {
                    "processed_count": len(written_keys),
                    "keys": written_keys,
                    "content_type": result.content_type,
                    "dimensions": len(result.embeddings[0]) if result.embeddings else 0,
                }
                console.print(RichJSON(json.dumps(result_data, indent=2)))

    except Exception as e:
        if debug:
            console.print_exception()
        else:
            console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


def _display_put_table(console: Console, keys, result):
    """Display put results in table format."""
    table = Table(title="Put Results")
    table.add_column("Key", style="cyan")
    table.add_column("Content Type", style="green")
    table.add_column("Dimensions", style="yellow")

    dims = len(result.embeddings[0]) if result.embeddings else 0
    for k in keys:
        table.add_row(k, result.content_type, str(dims))

    console.print(table)
    console.print(f"\n[green]Successfully wrote {len(keys)} vector(s).[/green]")


def _display_batch_table(console: Console, batch_result):
    """Display batch processing results in table format."""
    table = Table(title="Batch Processing Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Processed", str(batch_result.processed_count))
    table.add_row("Failed", str(batch_result.failed_count))
    table.add_row("Elapsed Time", f"{batch_result.elapsed_time:.2f}s")

    console.print(table)

    if batch_result.errors:
        error_table = Table(title="Errors")
        error_table.add_column("Source", style="red")
        error_table.add_column("Error", style="dim")
        for src, err in batch_result.errors:
            error_table.add_row(src, err)
        console.print(error_table)
