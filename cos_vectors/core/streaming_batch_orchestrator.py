"""Streaming batch orchestrator for cos-vectors-embed-cli.

Handles large-scale file processing with streaming generators
and parallel execution via ThreadPoolExecutor.
"""

import glob
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Dict, Generator, List, Optional, Tuple

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from cos_vectors.core.cos_vector_service import COSVectorService
from cos_vectors.core.embedding_provider import EmbeddingProvider
from cos_vectors.core.unified_processor import ProcessingResult, UnifiedProcessor
from cos_vectors.utils.models import (
    ProcessingInput,
    detect_content_type_from_extension,
    generate_vector_key,
)
from cos_vectors.utils.multimodal_helpers import (
    create_source_metadata,
    is_cos_uri,
    read_file_content,
    read_image_as_base64,
)


@dataclass
class BatchResult:
    """Result of a streaming batch processing operation.

    Attributes:
        processed_count: Number of successfully processed items.
        failed_count: Number of failed items.
        processed_keys: List of successfully written vector keys.
        errors: List of (source, error_message) tuples for failures.
        elapsed_time: Total processing time in seconds.
    """

    processed_count: int = 0
    failed_count: int = 0
    processed_keys: List[str] = field(default_factory=list)
    errors: List[Tuple[str, str]] = field(default_factory=list)
    elapsed_time: float = 0.0


class StreamingBatchOrchestrator:
    """Orchestrates streaming batch processing of files.

    Supports both local glob patterns and COS prefix matching.
    Uses ThreadPoolExecutor for parallel embedding generation
    and batched vector storage.
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        cos_service: COSVectorService,
        model_id: str,
        max_workers: int = 4,
        batch_size: int = 100,
        console: Optional[Console] = None,
        debug: bool = False,
    ):
        """Initialize the streaming batch orchestrator.

        Args:
            embedding_provider: Embedding provider instance.
            cos_service: COS vector service instance.
            model_id: Embedding model identifier.
            max_workers: Number of parallel worker threads.
            batch_size: Number of items per storage batch.
            console: Rich Console for output.
            debug: Enable debug logging.
        """
        self.embedding_provider = embedding_provider
        self.cos_service = cos_service
        self.model_id = model_id
        self.max_workers = max_workers
        self.batch_size = batch_size
        self.console = console or Console()
        self.debug = debug

    def process_streaming_batch(
        self,
        file_pattern: str,
        bucket_name: str,
        index_name: str,
        metadata: Optional[Dict[str, Any]] = None,
        filename_as_key: bool = False,
        key_prefix: Optional[str] = None,
        dimensions: Optional[int] = None,
    ) -> BatchResult:
        """Process a batch of files matching the pattern.

        Automatically detects whether the pattern is a local glob
        or COS prefix and uses the appropriate streaming strategy.

        Args:
            file_pattern: Local glob pattern or COS URI prefix.
            bucket_name: Target vector bucket.
            index_name: Target index.
            metadata: Optional user metadata to attach.
            filename_as_key: Use filenames as vector keys.
            key_prefix: Optional key prefix.
            dimensions: Expected embedding dimensions.

        Returns:
            BatchResult with processing statistics.
        """
        start_time = time.time()
        result = BatchResult()

        if is_cos_uri(file_pattern):
            self._process_cos_streaming(
                file_pattern, bucket_name, index_name,
                metadata, filename_as_key, key_prefix,
                dimensions, result,
            )
        else:
            self._process_local_streaming(
                file_pattern, bucket_name, index_name,
                metadata, filename_as_key, key_prefix,
                dimensions, result,
            )

        result.elapsed_time = time.time() - start_time
        return result

    def _process_local_streaming(
        self,
        file_pattern: str,
        bucket_name: str,
        index_name: str,
        metadata: Optional[Dict[str, Any]],
        filename_as_key: bool,
        key_prefix: Optional[str],
        dimensions: Optional[int],
        result: BatchResult,
    ) -> None:
        """Process local files matching a glob pattern.

        Uses iglob for memory-efficient file iteration.
        """
        chunks = list(self._stream_local_chunks(file_pattern))

        if not chunks:
            self.console.print(
                f"[yellow]Warning: No files matched pattern '{file_pattern}'[/yellow]"
            )
            return

        total_files = sum(len(chunk) for chunk in chunks)
        self.console.print(
            f"Found {total_files} file(s) matching '{file_pattern}'"
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console,
        ) as progress:
            task = progress.add_task("Processing files...", total=total_files)

            for chunk in chunks:
                self._process_chunk(
                    file_paths=chunk,
                    bucket_name=bucket_name,
                    index_name=index_name,
                    metadata=metadata,
                    filename_as_key=filename_as_key,
                    key_prefix=key_prefix,
                    dimensions=dimensions,
                    result=result,
                    progress=progress,
                    task_id=task,
                )

    def _stream_local_chunks(
        self, file_pattern: str
    ) -> Generator[List[str], None, None]:
        """Stream local files in chunks using iglob.

        Args:
            file_pattern: Glob pattern.

        Yields:
            Lists of file paths, each up to batch_size.
        """
        chunk: List[str] = []

        for filepath in glob.iglob(file_pattern, recursive=True):
            if os.path.isfile(filepath):
                chunk.append(filepath)
                if len(chunk) >= self.batch_size:
                    yield chunk
                    chunk = []

        if chunk:
            yield chunk

    def _process_cos_streaming(
        self,
        cos_uri: str,
        bucket_name: str,
        index_name: str,
        metadata: Optional[Dict[str, Any]],
        filename_as_key: bool,
        key_prefix: Optional[str],
        dimensions: Optional[int],
        result: BatchResult,
    ) -> None:
        """Process COS objects matching a prefix.

        Note: COS streaming requires COS client for object listing.
        This is a placeholder for future implementation.
        """
        self.console.print(
            "[yellow]COS prefix streaming is not yet fully implemented. "
            "Please use local file patterns for now.[/yellow]"
        )

    def _process_chunk(
        self,
        file_paths: List[str],
        bucket_name: str,
        index_name: str,
        metadata: Optional[Dict[str, Any]],
        filename_as_key: bool,
        key_prefix: Optional[str],
        dimensions: Optional[int],
        result: BatchResult,
        progress: Optional[Progress] = None,
        task_id: Optional[int] = None,
    ) -> None:
        """Process a chunk of files with parallel embedding.

        Args:
            file_paths: List of file paths to process.
            bucket_name: Target vector bucket.
            index_name: Target index.
            metadata: User metadata.
            filename_as_key: Use filename as key.
            key_prefix: Key prefix.
            dimensions: Embedding dimensions.
            result: BatchResult to accumulate into.
            progress: Rich Progress bar.
            task_id: Progress task ID.
        """
        vectors: List[Dict[str, Any]] = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_path = {}

            for filepath in file_paths:
                future = executor.submit(
                    self._process_single_file,
                    filepath=filepath,
                    metadata=metadata,
                    filename_as_key=filename_as_key,
                    key_prefix=key_prefix,
                    dimensions=dimensions,
                )
                future_to_path[future] = filepath

            for future in as_completed(future_to_path):
                filepath = future_to_path[future]
                try:
                    vector = future.result()
                    if vector:
                        vectors.append(vector)
                except Exception as e:
                    result.failed_count += 1
                    result.errors.append((filepath, str(e)))
                    if self.debug:
                        self.console.print(
                            f"[red]Error processing {filepath}: {e}[/red]"
                        )
                finally:
                    if progress and task_id is not None:
                        progress.advance(task_id)

        # Batch store vectors
        if vectors:
            try:
                keys = self.cos_service.put_vectors_batch(
                    bucket_name=bucket_name,
                    index_name=index_name,
                    vectors=vectors,
                )
                result.processed_count += len(keys)
                result.processed_keys.extend(keys)
            except Exception as e:
                result.failed_count += len(vectors)
                for v in vectors:
                    result.errors.append((v.get("key", "unknown"), str(e)))

    def _process_single_file(
        self,
        filepath: str,
        metadata: Optional[Dict[str, Any]],
        filename_as_key: bool,
        key_prefix: Optional[str],
        dimensions: Optional[int],
    ) -> Optional[Dict[str, Any]]:
        """Process a single file: read → embed → assemble vector.

        Args:
            filepath: Local file path.
            metadata: User metadata.
            filename_as_key: Use filename as key.
            key_prefix: Key prefix.
            dimensions: Embedding dimensions.

        Returns:
            Assembled vector dict, or None if processing fails.
        """
        content_type = detect_content_type_from_extension(filepath)

        # Read content
        if content_type == "image":
            content_data = read_image_as_base64(filepath)
        else:
            content_data = read_file_content(filepath)

        if not content_data:
            return None

        # Generate embedding
        if content_type == "image":
            embedding = self.embedding_provider.embed_image(
                image_base64=content_data,
                model=self.model_id,
                dimensions=dimensions,
            )
        else:
            embeddings = self.embedding_provider.embed_texts(
                texts=[content_data],
                model=self.model_id,
                dimensions=dimensions,
            )
            embedding = embeddings[0]

        # Generate key
        key = generate_vector_key(
            filename_as_key=filename_as_key,
            source_location=filepath,
            key_prefix=key_prefix,
        )

        # Build metadata
        vector_metadata = create_source_metadata(
            content_type=content_type,
            source_location=filepath,
        )
        if metadata:
            vector_metadata.update(metadata)

        return {
            "key": key,
            "data": {"float32": embedding},
            "metadata": vector_metadata,
        }
