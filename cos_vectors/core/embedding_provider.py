"""Embedding Provider abstraction for cos-vectors-embed-cli.

Defines the EmbeddingProvider ABC and concrete implementations.
Uses the Provider pattern to support pluggable embedding services.

NOTE: Uses stdlib urllib instead of the openai SDK to avoid dependency
issues in environments where openai>=1.0.0 is unavailable.
"""

import json
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from rich.console import Console


class EmbeddingProvider(ABC):
    """Abstract base class for embedding model providers.

    All embedding providers must implement embed_texts() and embed_image()
    methods that convert content into embedding vectors.
    """

    @abstractmethod
    def embed_texts(
        self,
        texts: List[str],
        model: str,
        dimensions: Optional[int] = None,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> List[List[float]]:
        """Convert a list of text strings to embedding vectors.

        Args:
            texts: List of text strings to embed.
            model: Model identifier.
            dimensions: Optional output dimensions (if API supports).
            extra_params: Additional model-specific parameters.

        Returns:
            List of embedding vectors (each a list of floats).
        """
        ...

    @abstractmethod
    def embed_image(
        self,
        image_base64: str,
        model: str,
        dimensions: Optional[int] = None,
    ) -> List[float]:
        """Convert a base64-encoded image to an embedding vector.

        Args:
            image_base64: Base64-encoded image string.
            model: Model identifier.
            dimensions: Optional output dimensions.

        Returns:
            Embedding vector (list of floats).
        """
        ...


class EmbeddingAPIError(Exception):
    """Raised when the embedding API returns an error response."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"Embedding API error (HTTP {status_code}): {message}")


class OpenAICompatibleProvider(EmbeddingProvider):
    """Provider using the OpenAI /v1/embeddings compatible protocol.

    Works with any embedding service that implements the OpenAI
    embeddings API format (e.g. OpenAI, vLLM, Ollama, etc.).

    Uses stdlib urllib.request — no third-party HTTP library needed.
    """

    def __init__(
        self,
        api_base: str,
        api_key: str,
        default_model: str = "text-embedding-3-small",
        console: Optional[Console] = None,
        debug: bool = False,
        timeout: int = 120,
    ):
        """Initialize OpenAI compatible provider.

        Args:
            api_base: API base URL (e.g. 'https://api.openai.com/v1').
            api_key: API key for authentication.
            default_model: Default model name.
            console: Rich Console for output.
            debug: Enable debug logging.
            timeout: HTTP request timeout in seconds.
        """
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.default_model = default_model
        self.console = console or Console()
        self.debug = debug
        self.timeout = timeout

        # Build the embeddings endpoint URL
        self._embeddings_url = f"{self.api_base}/embeddings"

    def _call_api(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send a POST request to the /v1/embeddings endpoint.

        Args:
            payload: JSON-serializable request body.

        Returns:
            Parsed JSON response as a dict.

        Raises:
            EmbeddingAPIError: If the API returns a non-2xx status.
            ConnectionError: If the request fails at the network level.
        """
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        if self.debug:
            self.console.print(
                f"[dim]POST {self._embeddings_url}  payload_size={len(data)}[/dim]"
            )

        req = urllib.request.Request(
            self._embeddings_url,
            data=data,
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body)
        except urllib.error.HTTPError as exc:
            # Read the error body for a better message
            err_body = ""
            try:
                err_body = exc.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            raise EmbeddingAPIError(exc.code, err_body or str(exc)) from exc
        except urllib.error.URLError as exc:
            raise ConnectionError(
                f"Failed to connect to embedding API at {self._embeddings_url}: {exc.reason}"
            ) from exc

    def embed_texts(
        self,
        texts: List[str],
        model: Optional[str] = None,
        dimensions: Optional[int] = None,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> List[List[float]]:
        """Embed texts using OpenAI compatible /v1/embeddings API.

        Args:
            texts: List of text strings.
            model: Model name (falls back to default_model).
            dimensions: Optional output dimensions.
            extra_params: Additional parameters for the API call.

        Returns:
            List of embedding vectors.
        """
        model = model or self.default_model

        payload: Dict[str, Any] = {
            "input": texts,
            "model": model,
        }

        if dimensions is not None:
            payload["dimensions"] = dimensions

        if extra_params:
            payload.update(extra_params)

        if self.debug:
            self.console.print(
                f"[dim]Embedding {len(texts)} text(s) with model '{model}'[/dim]"
            )

        result = self._call_api(payload)

        # Sort by index to ensure correct order (OpenAI format: data[].index)
        data_items = sorted(result["data"], key=lambda x: x["index"])
        return [item["embedding"] for item in data_items]

    def embed_image(
        self,
        image_base64: str,
        model: Optional[str] = None,
        dimensions: Optional[int] = None,
    ) -> List[float]:
        """Embed an image using OpenAI compatible API.

        Note: Image embedding support varies by API provider.
        The image is sent as a base64-encoded string in the input field.

        Args:
            image_base64: Base64-encoded image data.
            model: Model name.
            dimensions: Optional output dimensions.

        Returns:
            Embedding vector.
        """
        model = model or self.default_model

        payload: Dict[str, Any] = {
            "input": [image_base64],
            "model": model,
        }

        if dimensions is not None:
            payload["dimensions"] = dimensions

        if self.debug:
            self.console.print(
                f"[dim]Embedding image with model '{model}'[/dim]"
            )

        result = self._call_api(payload)
        return result["data"][0]["embedding"]


def get_provider(
    provider_type: str = "openai-compatible",
    **kwargs,
) -> EmbeddingProvider:
    """Factory function to create an embedding provider.

    Args:
        provider_type: Provider type identifier.
            Currently supported: 'openai-compatible'.
        **kwargs: Provider-specific configuration arguments.

    Returns:
        Configured EmbeddingProvider instance.

    Raises:
        ValueError: If provider_type is not supported.
    """
    providers = {
        "openai-compatible": OpenAICompatibleProvider,
    }

    provider_class = providers.get(provider_type)
    if provider_class is None:
        supported = ", ".join(providers.keys())
        raise ValueError(
            f"Unknown provider type: '{provider_type}'. "
            f"Supported types: {supported}"
        )

    return provider_class(**kwargs)
