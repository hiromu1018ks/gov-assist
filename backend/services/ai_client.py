"""AI client service for SAKURA AI Engine (OpenAI-compatible API)."""

import os
import logging
from dataclasses import dataclass

from openai import AsyncOpenAI

logger = logging.getLogger("govassist")


@dataclass(frozen=True)
class ModelConfig:
    """Configuration for an AI model."""
    display_name: str
    max_tokens: int
    temperature: float
    max_input_chars: int
    json_forced: bool


# §4.2 モデル設定テーブル
MODEL_CONFIGS: dict[str, ModelConfig] = {
    "kimi-k2.5": ModelConfig(
        display_name="Kimi K2.5",
        max_tokens=4096,
        temperature=0.3,
        max_input_chars=8000,
        json_forced=True,
    ),
}


def get_model_config(model_id: str) -> ModelConfig:
    """Get configuration for a model. Raises KeyError if model not found."""
    return MODEL_CONFIGS[model_id]


class AIClientError(Exception):
    """Raised when AI API call fails."""

    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        self.message = message
        super().__init__(message)


class AIClient:
    """Async client for SAKURA AI Engine."""

    def __init__(self, api_key: str, base_url: str):
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=60.0,
        )
        self._base_url = base_url

    async def complete(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        temperature: float,
        request_id: str,
    ) -> str:
        """Call AI engine and return response text.

        Raises AIClientError on failure.
        """
        raise NotImplementedError


def create_ai_client() -> AIClient:
    """Factory: create AIClient from environment variables."""
    api_key = os.getenv("AI_ENGINE_API_KEY")
    if not api_key:
        raise ValueError("AI_ENGINE_API_KEY environment variable is not set")
    base_url = os.getenv("AI_ENGINE_BASE_URL")
    if not base_url:
        raise ValueError("AI_ENGINE_BASE_URL environment variable is not set")
    return AIClient(api_key=api_key, base_url=base_url)
