"""COS Vector Storage service for cos-vectors-embed.

Wraps CosVectorsClient from cos-python-sdk-v5 for vector operations.
Uses Domain parameter (not Endpoint) for proper vector API routing.
"""

import math
from typing import Any, Dict, List, Optional

from rich.console import Console

from cos_vectors.utils.config import get_cos_config


# Maximum vectors per single put_vectors API call
MAX_VECTORS_PER_BATCH = 500


class COSVectorService:
    """COS Vector Storage service wrapper.

    Encapsulates CosVectorsClient operations for put_vectors,
    query_vectors, and get_index. Uses Domain parameter in CosConfig
    because the vectors API does not use {bucket}.{endpoint} URL
    construction.
    """

    def __init__(
        self,
        region: str,
        domain: str,
        secret_id: Optional[str] = None,
        secret_key: Optional[str] = None,
        token: Optional[str] = None,
        debug: bool = False,
        console: Optional[Console] = None,
    ):
        """Initialize COS Vector Service.

        Args:
            region: COS region, e.g. 'ap-guangzhou'.
            domain: Vectors service domain, e.g. 'vectors.ap-guangzhou.coslake.com'.
            secret_id: COS SecretId (falls back to env var).
            secret_key: COS SecretKey (falls back to env var).
            token: Temporary token (falls back to env var).
            debug: Enable debug logging.
            console: Rich Console for output.
        """
        from qcloud_cos import CosVectorsClient

        self.debug = debug
        self.console = console or Console()

        config = get_cos_config(
            region=region,
            domain=domain,
            secret_id=secret_id,
            secret_key=secret_key,
            token=token,
        )
        self._client = CosVectorsClient(config)

    def put_vectors_batch(
        self,
        bucket_name: str,
        index_name: str,
        vectors: List[Dict[str, Any]],
    ) -> List[str]:
        """Batch write vectors to COS vector index.

        Automatically splits into multiple API calls if vectors exceed
        the per-call limit (500).

        Each vector should be formatted as:
        {
            "key": "vector_key",
            "data": {"float32": [0.1, 0.2, ...]},
            "metadata": {"key": "value"}  # optional
        }

        Args:
            bucket_name: Vector bucket name.
            index_name: Index name.
            vectors: List of vector dicts.

        Returns:
            List of written vector keys.

        Raises:
            Exception: If COS API call fails.
        """
        if not vectors:
            return []

        written_keys = []
        total_batches = math.ceil(len(vectors) / MAX_VECTORS_PER_BATCH)

        for i in range(0, len(vectors), MAX_VECTORS_PER_BATCH):
            batch = vectors[i : i + MAX_VECTORS_PER_BATCH]
            batch_num = (i // MAX_VECTORS_PER_BATCH) + 1

            if self.debug:
                self.console.print(
                    f"[dim]Writing batch {batch_num}/{total_batches} "
                    f"({len(batch)} vectors)[/dim]"
                )

            try:
                # put_vectors returns only response headers
                self._client.put_vectors(
                    Bucket=bucket_name,
                    Index=index_name,
                    Vectors=batch,
                )
                written_keys.extend(v["key"] for v in batch)
            except Exception as e:
                self.console.print(
                    f"[red]Error writing batch {batch_num}: {e}[/red]"
                )
                raise

        return written_keys

    def query_vectors(
        self,
        bucket_name: str,
        index_name: str,
        query_embedding: List[float],
        top_k: int = 5,
        filter_expr: Optional[Dict[str, Any]] = None,
        return_metadata: bool = True,
        return_distance: bool = True,
    ) -> List[Dict[str, Any]]:
        """Query vectors by similarity search.

        Args:
            bucket_name: Vector bucket name.
            index_name: Index name.
            query_embedding: Query vector (list of floats).
            top_k: Number of results to return.
            filter_expr: Optional metadata filter dict (JSON object).
            return_metadata: Whether to return metadata.
            return_distance: Whether to return distance scores.

        Returns:
            List of result dicts containing matched vectors.
        """
        kwargs: Dict[str, Any] = {
            "Bucket": bucket_name,
            "Index": index_name,
            "QueryVector": {"float32": query_embedding},
            "TopK": top_k,
        }

        if filter_expr is not None:
            kwargs["Filter"] = filter_expr

        if return_distance is not None:
            kwargs["ReturnDistance"] = return_distance

        if return_metadata is not None:
            kwargs["ReturnMetaData"] = return_metadata

        if self.debug:
            self.console.print(
                f"[dim]Querying index '{index_name}' with top_k={top_k}[/dim]"
            )

        # query_vectors returns (response_headers, data) tuple
        _, data = self._client.query_vectors(**kwargs)
        return data

    def get_index(
        self,
        bucket_name: str,
        index_name: str,
    ) -> Dict[str, Any]:
        """Get index information including dimension.

        Args:
            bucket_name: Vector bucket name.
            index_name: Index name.

        Returns:
            Dict containing index information (dimension, metric, etc.).
        """
        if self.debug:
            self.console.print(
                f"[dim]Getting index info for '{index_name}'[/dim]"
            )

        # get_index returns (response_headers, data) tuple
        _, data = self._client.get_index(
            Bucket=bucket_name,
            Index=index_name,
        )
        return data
