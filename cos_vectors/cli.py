"""CLI entry point for cos-vectors-embed-cli.

Defines the Click Group with global options and registers subcommands.
"""

import sys

import click
from rich.console import Console

from cos_vectors.__version__ import __version__
from cos_vectors.commands.embed_put import embed_put
from cos_vectors.commands.embed_query import embed_query


@click.group()
@click.option(
    "--region",
    type=str,
    default=None,
    envvar="COS_REGION",
    help="COS region (e.g. ap-guangzhou). Falls back to COS_REGION env var.",
)
@click.option(
    "--domain",
    type=str,
    default=None,
    envvar="COS_DOMAIN",
    help="COS Vectors service domain (e.g. vectors.ap-guangzhou.coslake.com). "
    "Falls back to COS_DOMAIN env var.",
)
@click.option(
    "--debug",
    is_flag=True,
    default=False,
    help="Enable debug output with detailed logging.",
)
@click.version_option(version=__version__, prog_name="cos-vectors-embed-cli")
@click.pass_context
def cli(ctx, region, domain, debug):
    """COS Vectors Embed CLI - Vectorize content and store in COS Vector Buckets."""
    ctx.ensure_object(dict)

    console = Console()

    ctx.obj["region"] = region
    ctx.obj["domain"] = domain
    ctx.obj["debug"] = debug
    ctx.obj["console"] = console


# Register subcommands
cli.add_command(embed_put, name="put")
cli.add_command(embed_query, name="query")


def main():
    """Main entry point with error handling."""
    try:
        cli()
    except KeyboardInterrupt:
        console = Console()
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")
        sys.exit(130)
    except Exception as e:
        console = Console()
        console.print(f"\n[red]Error: {e}[/red]")
        sys.exit(1)
