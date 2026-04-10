"""Unified processing pipeline for cos-vectors-embed.

Orchestrates the full flow: content preparation → embedding → vector assembly.
"""

import base64
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from qcloud_cos import CosS3Client
from rich.console import Console

from cos_vectors.core.cos_vector_service import COSVectorService
from cos_vectors.core.embedding_provider import EmbeddingProvider
from cos_vectors.utils.models import ProcessingInput, generate_vector_key
from cos_vectors.utils.multimodal_helpers import (
    create_source_metadata,
    is_cos_uri,
    is_http_url,
    parse_cos_uri,
    read_file_content,
    read_file_content_from_url,
    read_image_as_base64,
)


@dataclass
class ProcessingResult:
    """Result of the unified processing pipeline.

    Attributes:
        vectors: List of assembled vector dicts ready for put_vectors.
        embeddings: Raw embedding vectors from the provider.
        content_type: Type of content processed.
        source_locations: Source paths/URIs of processed content.
    """

    vectors: List[Dict[str, Any]] = field(default_factory=list)
    embeddings: List[List[float]] = field(default_factory=list)
    content_type: str = "text"
    source_locations: List[str] = field(default_factory=list)


class UnifiedProcessor:
    """Unified processing pipeline.

    Orchestrates: content preparation → embedding generation → vector assembly.
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        cos_service: COSVectorService,
        model_id: str,
        console: Optional[Console] = None,
        debug: bool = False,
        cos_s3_client: Optional[CosS3Client] = None,
    ):
        """Initialize the unified processor.

        Args:
            embedding_provider: Embedding provider instance.
            cos_service: COS vector service instance.
            model_id: Embedding model identifier.
            console: Rich Console for output.
            debug: Enable debug logging.
            cos_s3_client: Optional COS S3 client for reading COS objects.
        """
        self.embedding_provider = embedding_provider
        self.cos_service = cos_service
        self.model_id = model_id
        self.console = console or Console()
        self.debug = debug
        self.cos_s3_client = cos_s3_client

    def process(
        self,
        processing_input: ProcessingInput,
        bucket_name: str,
        index_name: str,
        dimensions: Optional[int] = None,
    ) -> ProcessingResult:
        """Run the full processing pipeline for a single input.

        Flow:
        1. Get index dimension (if not provided)
        2. Prepare content (read files, encode images)
        3. Generate embeddings
        4. Assemble vector data

        Args:
            processing_input: Input to process.
            bucket_name: Target vector bucket.
            index_name: Target index.
            dimensions: Expected embedding dimensions (auto-detected if None).

        Returns:
            ProcessingResult with assembled vectors.
        """
        # Step 1: Auto-detect dimensions from index if not provided
        if dimensions is None:
            try:
                index_info = self.cos_service.get_index(bucket_name, index_name)
                dimensions = index_info.get("dimension") or index_info.get("Dimension")
                if self.debug and dimensions:
                    self.console.print(
                        f"[dim]Auto-detected index dimension: {dimensions}[/dim]"
                    )
            except (OSError, ValueError, ConnectionError, RuntimeError) as e:
                if self.debug:
                    self.console.print(
                        f"[dim]Could not auto-detect dimensions: {e}[/dim]"
                    )

        # Step 2: Prepare content
        content_data = self._prepare_content(processing_input)

        # Step 3: Generate embeddings
        embeddings = self._generate_embeddings(
            content_data,
            processing_input.content_type,
            dimensions=dimensions,
        )

        # Step 4: Assemble vectors
        vectors = self._prepare_vectors(
            embeddings=embeddings,
            processing_input=processing_input,
        )

        return ProcessingResult(
            vectors=vectors,
            embeddings=embeddings,
            content_type=processing_input.content_type,
            source_locations=[processing_input.source_location or "inline"],
        )

    def process_query(
        self,
        processing_input: ProcessingInput,
        dimensions: Optional[int] = None,
    ) -> List[float]:
        """Process a query input and return the embedding vector.

        Args:
            processing_input: Query input to process.
            dimensions: Expected embedding dimensions.

        Returns:
            Embedding vector for the query.
        """
        content_data = self._prepare_content(processing_input)
        embeddings = self._generate_embeddings(
            content_data,
            processing_input.content_type,
            dimensions=dimensions,
        )

        if not embeddings:
            raise ValueError("Failed to generate embedding for query input.")

        return embeddings[0]

    def store_vectors(
        self,
        result: ProcessingResult,
        bucket_name: str,
        index_name: str,
    ) -> List[str]:
        """Store processed vectors to COS.

        Args:
            result: ProcessingResult containing assembled vectors.
            bucket_name: Target vector bucket.
            index_name: Target index.

        Returns:
            List of written vector keys.
        """
        if not result.vectors:
            return []

        return self.cos_service.put_vectors_batch(
            bucket_name=bucket_name,
            index_name=index_name,
            vectors=result.vectors,
        )

    def _prepare_content(self, processing_input: ProcessingInput) -> Any:
        """Prepare content for embedding based on content type.

        Args:
            processing_input: Input with content info.

        Returns:
            Prepared content data (text string, base64 image, etc.).
        """
        if processing_input.data is not None:
            # Data already loaded (e.g. --text-value inline text)
            return processing_input.data

        source = processing_input.source_location
        if source is None:
            raise ValueError("No data or source_location provided.")

        content_type = processing_input.content_type

        if content_type == "text":
            return self._read_text_content(source)
        elif content_type == "image":
            return self._read_image_content(source)
        else:
            raise ValueError(f"Unsupported content type: {content_type}")

    def _read_text_content(self, source: str) -> str:
        """Read text content from various sources.

        Args:
            source: Local path, COS URI, or HTTP URL.

        Returns:
            Text content string.
        """
        if is_http_url(source):
            return read_file_content_from_url(source)
        elif is_cos_uri(source):
            if self.cos_s3_client is None:
                raise ValueError(
                    f"Cannot read COS URI '{source}': COS S3 client not configured. "
                    "Ensure COS_SECRET_ID, COS_SECRET_KEY, and COS_REGION are set."
                )
            bucket, key = parse_cos_uri(source)
            response = self.cos_s3_client.get_object(Bucket=bucket, Key=key)
            return response["Body"].get_raw_stream().read().decode("utf-8")
        else:
            return read_file_content(source)

    def _read_image_content(self, source: str) -> str:
        """Read image content and return base64-encoded string.

        Args:
            source: Local image file path or COS URI.

        Returns:
            Base64-encoded image string.
        """
        if is_cos_uri(source):
            if self.cos_s3_client is None:
                raise ValueError(
                    f"Cannot read COS URI '{source}': COS S3 client not configured. "
                    "Ensure COS_SECRET_ID, COS_SECRET_KEY, and COS_REGION are set."
                )
            bucket, key = parse_cos_uri(source)
            response = self.cos_s3_client.get_object(Bucket=bucket, Key=key)
            image_bytes = response["Body"].get_raw_stream().read()
            return base64.b64encode(image_bytes).decode("utf-8")
        elif is_http_url(source):
            raise NotImplementedError(
                f"Reading images from HTTP URL '{source}' is not yet supported. "
                "Use local image files or COS URIs."
            )
        return read_image_as_base64(source)

    def _generate_embeddings(
        self,
        content_data: Any,
        content_type: str,
        dimensions: Optional[int] = None,
    ) -> List[List[float]]:
        """Generate embeddings for the prepared content.

        Args:
            content_data: Prepared content (text string or base64 image).
            content_type: Content type ('text' or 'image').
            dimensions: Optional output dimensions.

        Returns:
            List of embedding vectors.
        """
        if content_type == "text":
            texts = [content_data] if isinstance(content_data, str) else content_data
            return self.embedding_provider.embed_texts(
                texts=texts,
                model=self.model_id,
                dimensions=dimensions,
            )
        elif content_type == "image":
            embedding = self.embedding_provider.embed_image(
                image_base64=content_data,
                model=self.model_id,
                dimensions=dimensions,
            )
            return [embedding]
        else:
            raise ValueError(f"Unsupported content type for embedding: {content_type}")

    def _prepare_vectors(
        self,
        embeddings: List[List[float]],
        processing_input: ProcessingInput,
    ) -> List[Dict[str, Any]]:
        """Assemble embedding results into COS Vectors API format.

        Format: {"key": "xxx", "data": {"float32": [...]}, "metadata": {...}}

        Args:
            embeddings: List of embedding vectors.
            processing_input: Original processing input (for key/metadata).

        Returns:
            List of vector dicts ready for put_vectors.
        """
        vectors = []

        for embedding in embeddings:
            # Generate vector key
            key = generate_vector_key(
                custom_key=processing_input.custom_key,
                filename_as_key=processing_input.filename_as_key,
                source_location=processing_input.source_location,
                key_prefix=processing_input.key_prefix,
            )

            # Build metadata: system source metadata + user metadata
            metadata = create_source_metadata(
                content_type=processing_input.content_type,
                source_location=processing_input.source_location,
            )
            if processing_input.metadata:
                metadata.update(processing_input.metadata)

            vector = {
                "key": key,
                "data": {"float32": embedding},
            }
            if metadata:
                vector["metadata"] = metadata

            vectors.append(vector)

        return vectors
