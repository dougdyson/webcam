"""
Client for the Pyra vision service - an LFM2.5-VL model served natively from
the pyra repo (scripts/vision_service.py, default port 9920).

Duck-type compatible with OllamaClient (is_available / describe_image), so it
drops into DescriptionService unchanged:

    from src.pyra_vision import PyraVisionClient
    client = PyraVisionClient()
    service = DescriptionService(ollama_client=client, config=...)

Raises OllamaError on failure so existing error handling applies verbatim.
"""
import base64
import logging
import os
import time
from dataclasses import dataclass
from typing import Union

import requests

from ..ollama.client import OllamaError

logger = logging.getLogger(__name__)


@dataclass
class PyraVisionConfig:
    """Configuration for the Pyra vision service client."""
    base_url: str = "http://localhost:9920"
    timeout: float = 30.0
    max_retries: int = 2
    max_tokens: int = 64
    # Per-request backend selection on the vision service:
    #   "finetuned" - the in-process LFM2.5-VL model loaded by the service
    #   "ollama"    - generalist multimodal model proxied via Ollama
    backend: str = "finetuned"
    model: str = None  # ollama model override (service default if None)

    def __post_init__(self):
        self.base_url = self.base_url.rstrip("/")

    @classmethod
    def from_env(cls) -> "PyraVisionConfig":
        """Build config from environment variables, falling back to defaults."""
        base_url = os.getenv("ZIGGY_VISION_BASE_URL") or os.getenv(
            "PYRA_VISION_BASE_URL",
            cls.base_url,
        )
        return cls(
            base_url=base_url,
            timeout=float(
                os.getenv("ZIGGY_VISION_TIMEOUT")
                or os.getenv("PYRA_VISION_TIMEOUT", cls.timeout)
            ),
            max_retries=int(
                os.getenv("ZIGGY_VISION_MAX_RETRIES")
                or os.getenv("PYRA_VISION_MAX_RETRIES", cls.max_retries)
            ),
            max_tokens=int(
                os.getenv("ZIGGY_VISION_MAX_TOKENS")
                or os.getenv("PYRA_VISION_MAX_TOKENS", cls.max_tokens)
            ),
            backend=os.getenv("ZIGGY_VISION_BACKEND")
            or os.getenv("PYRA_VISION_BACKEND", cls.backend),
            model=os.getenv("ZIGGY_VISION_MODEL")
            or os.getenv("PYRA_VISION_MODEL")
            or None,
        )


class PyraVisionClient:
    """
    Client for the Pyra vision service HTTP API.

    Same interface as OllamaClient (is_available, describe_image) so it can be
    injected into DescriptionService as a drop-in provider.
    """

    def __init__(self, config: PyraVisionConfig = None):
        self.config = config or PyraVisionConfig()
        logger.info(f"Initialized PyraVisionClient at {self.config.base_url}")

    def is_available(self) -> bool:
        """Check the vision service health endpoint."""
        try:
            response = requests.get(
                f"{self.config.base_url}/health", timeout=self.config.timeout
            )
            response.raise_for_status()
            return response.json().get("status") == "ok"
        except requests.exceptions.RequestException as e:
            logger.debug(f"Pyra vision service unavailable: {e}")
            return False
        except ValueError as e:
            logger.warning(f"Pyra vision health check response invalid: {e}")
            return False

    def describe_image(
        self,
        image_data: Union[bytes, str],
        prompt: str = None,
    ) -> str:
        """
        Generate a description for an image via the Pyra vision service.

        Args:
            image_data: Image as JPEG/PNG bytes or base64 string
            prompt: Optional prompt override (service default is the
                    service default prompt)

        Returns:
            Generated description text

        Raises:
            OllamaError: If description generation fails after retries
        """
        if isinstance(image_data, bytes):
            image_b64 = base64.b64encode(image_data).decode("utf-8")
        else:
            image_b64 = image_data

        payload = {
            "image": image_b64,
            "max_tokens": self.config.max_tokens,
            "backend": self.config.backend,
        }
        if self.config.model:
            payload["model"] = self.config.model
        if prompt:
            payload["prompt"] = prompt

        last_error = None
        for attempt in range(self.config.max_retries + 1):
            try:
                response = requests.post(
                    f"{self.config.base_url}/describe/base64",
                    json=payload,
                    timeout=self.config.timeout,
                )
                response.raise_for_status()

                data = response.json()
                description = data.get("description", "").strip()
                if not description:
                    raise OllamaError("Empty description from Pyra vision service")

                logger.debug(
                    f"Pyra vision description ({data.get('elapsed_ms')}ms): "
                    f"{description[:100]}..."
                )
                return description

            except requests.exceptions.RequestException as e:
                last_error = e
                if attempt < self.config.max_retries:
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"Pyra vision request failed (attempt {attempt + 1}), "
                        f"retrying in {wait_time}s: {e}"
                    )
                    time.sleep(wait_time)
                    continue

        raise OllamaError(
            "Pyra vision service request failed after all retries", last_error
        )
