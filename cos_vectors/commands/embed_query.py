"""Query subcommand for cos-vectors-embed-cli.

Vectorizes query input and performs similarity search on COS Vector index.
"""

import json
from typing import Any, Dict, Optional

import click
from rich.console import Console
from rich.json import JSON as RichJSON
from rich.table import Table

from cos_vectors.core.cos_vector_service import COSVectorService
from cos_vectors.core.embedding_provider import get_provider
from cos_vectors.core.unified_processor import UnifiedProcessor
from cos_vectors.utils.config import get_domain, get_region
from cos_vectors.utils.models import prepare_processing_input


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
    help="Direct text string to query with.",
)
@click.option(
    "--text",
    default=None,
    help="Local text file containing the query.",
)
@click.option(
    "--image",
    default=None,
    help="Local image file to query with.",
)
@click.option(
    "--top-k",
    default=5,
    type=int,
    help="Number of results to return. Default: 5.",
)
@click.option(
    "--filter",
    "filter_expr",
    default=None,
    help="Metadata filter expression.",
)
@click.option(
    "--return-distance/--no-return-distance",
    default=True,
    help="Whether to return distance scores. Default: true.",
)
@click.option(
    "--return-metadata/--no-return-metadata",
    default=True,
    help="Whether to return metadata. Default: true.",
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
def embed_query(
    ctx,
    vector_bucket_name,
    index_name,
    model_id,
    text_value,
    text,
    image,
    top_k,
    filter_expr,
    return_distance,
    return_metadata,
    provider,
    embedding_api_base,
    embedding_api_key,
    output,
    region,
    domain,
):
    """Query a COS vector index by similarity search."""
    console: Console = ctx.obj["console"]
    debug: bool = ctx.obj["debug"]

    # Resolve region and domain
    region = get_region(region or ctx.obj.get("region"))
    domain = get_domain(domain or ctx.obj.get("domain"))

    # Validate inputs
    if not any([text_value, text, image]):
        raise click.UsageError(
            "At least one query input is required: "
            "--text-value, --text, or --image"
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

        processor = UnifiedProcessor(
            embedding_provider=embedding_provider,
            cos_service=cos_service,
            model_id=model_id,
            console=console,
            debug=debug,
        )

        # Prepare query input
        processing_input = prepare_processing_input(
            text_value=text_value,
            text=text,
            image=image,
        )

        # Generate query embedding
        if debug:
            console.print("[dim]Generating query embedding...[/dim]")

        query_embedding = processor.process_query(processing_input)

        if debug:
            console.print(
                f"[dim]Query embedding dimension: {len(query_embedding)}[/dim]"
            )

        # Execute similarity search
        results = cos_service.query_vectors(
            bucket_name=vector_bucket_name,
            index_name=index_name,
            query_embedding=query_embedding,
            top_k=top_k,
            filter_expr=filter_expr,
            return_metadata=return_metadata,
            return_distance=return_distance,
        )

        # Display results
        if output == "table":
            _display_results_table(console, results, return_distance, return_metadata)
        else:
            console.print(RichJSON(json.dumps(results, indent=2, ensure_ascii=False)))

    except Exception as e:
        if debug:
            console.print_exception()
        else:
            console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


def _display_results_table(
    console: Console,
    results: Any,
    return_distance: bool,
    return_metadata: bool,
):
    """Display query results in a Rich table.

    Args:
        console: Rich Console instance.
        results: Query results from COS API.
        return_distance: Whether distance was requested.
        return_metadata: Whether metadata was requested.
    """
    table = Table(title="Query Results")
    table.add_column("#", style="dim")
    table.add_column("Key", style="cyan")

    if return_distance:
        table.add_column("Distance", style="yellow")

    if return_metadata:
        table.add_column("Metadata", style="green")

    # Handle different result formats from COS API
    vectors = []
    if isinstance(results, dict):
        vectors = results.get("vectors", results.get("Vectors", []))
    elif isinstance(results, list):
        vectors = results

    for i, vec in enumerate(vectors, 1):
        row = [str(i)]

        # Key
        key = vec.get("key", vec.get("Key", "N/A"))
        row.append(str(key))

        # Distance
        if return_distance:
            distance = vec.get("distance", vec.get("Distance", "N/A"))
            row.append(f"{distance}")

        # Metadata
        if return_metadata:
            meta = vec.get("metadata", vec.get("Metadata", {}))
            if meta:
                row.append(json.dumps(meta, ensure_ascii=False)[:80])
            else:
                row.append("-")

        table.add_row(*row)

    console.print(table)
    console.print(f"\nReturned {len(vectors)} result(s)")
