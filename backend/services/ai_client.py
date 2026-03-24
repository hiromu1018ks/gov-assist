"""AI client service for SAKURA AI Engine (OpenAI-compatible API)."""

import os
import logging
from dataclasses import dataclass

import openai
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
    "Qwen3-Coder-30B-A3B-Instruct": ModelConfig(
        display_name="Qwen3-Coder 30B",
        max_tokens=4096,
        temperature=0.3,
        max_input_chars=8000,
        json_forced=True,
    ),
    "Qwen3-Coder-480B-A35B-Instruct-FP8": ModelConfig(
        display_name="Qwen3-Coder 480B",
        max_tokens=4096,
        temperature=0.3,
        max_input_chars=8000,
        json_forced=True,
    ),
    "gpt-oss-120b": ModelConfig(
        display_name="GPT-OSS 120B",
        max_tokens=4096,
        temperature=0.3,
        max_input_chars=8000,
        json_forced=True,
    ),
    "llm-jp-3.1-8x13b-instruct4": ModelConfig(
        display_name="llm-jp 3.1 8x13B",
        max_tokens=2048,
        temperature=0.3,
        max_input_chars=8000,
        json_forced=True,
    ),
    "preview/Kimi-K2.5": ModelConfig(
        display_name="Kimi K2.5",
        max_tokens=4096,
        temperature=0.3,
        max_input_chars=8000,
        json_forced=True,
    ),
    "preview/Phi-4-mini-instruct-cpu": ModelConfig(
        display_name="Phi-4 mini (CPU)",
        max_tokens=4096,
        temperature=0.3,
        max_input_chars=8000,
        json_forced=True,
    ),
    "preview/Phi-4-multimodal-instruct": ModelConfig(
        display_name="Phi-4 Multimodal",
        max_tokens=4096,
        temperature=0.3,
        max_input_chars=8000,
        json_forced=True,
    ),
    "preview/Qwen3-0.6B-cpu": ModelConfig(
        display_name="Qwen3 0.6B (CPU)",
        max_tokens=4096,
        temperature=0.3,
        max_input_chars=8000,
        json_forced=True,
    ),
    "preview/Qwen3-VL-30B-A3B-Instruct": ModelConfig(
        display_name="Qwen3-VL 30B",
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
        json_forced: bool = False,
    ) -> str:
        """Call AI engine and return response text.

        Raises AIClientError on failure.
        """
        kwargs: dict = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if json_forced:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = await self._client.chat.completions.create(**kwargs)
            if not response.choices:
                logger.error(
                    "AI API returned empty choices: request_id=%s model=%s",
                    request_id, model,
                )
                raise AIClientError("ai_invalid_response", "AI API が空の応答を返しました")
            return response.choices[0].message.content or ""

        except openai.APITimeoutError:
            logger.error(
                "AI API timeout: request_id=%s model=%s endpoint=%s",
                request_id, model, self._base_url,
            )
            raise AIClientError("ai_timeout", "AI応答がタイムアウトしました（60秒）")

        except openai.RateLimitError as e:
            logger.error(
                "AI API rate limit: request_id=%s model=%s status_code=429 error=%s",
                request_id, model, str(e),
            )
            raise AIClientError("ai_rate_limit", "AI APIのレート制限に達しました")

        except openai.APIStatusError as e:
            logger.error(
                "AI API error: request_id=%s model=%s status_code=%s error=%s",
                request_id, model, e.status_code, str(e),
            )
            raise AIClientError("ai_invalid_response", "AI API エラーが発生しました")

        except openai.APIConnectionError as e:
            logger.error(
                "AI API connection error: request_id=%s model=%s endpoint=%s error=%s",
                request_id, model, self._base_url, str(e),
            )
            raise AIClientError("ai_invalid_response", "AI API への接続に失敗しました")

        except AIClientError:
            raise

        except Exception as e:
            logger.error(
                "Unexpected AI client error: request_id=%s model=%s error=%s",
                request_id, model, str(e),
            )
            raise AIClientError("ai_invalid_response", "AI API で予期しないエラーが発生しました")


def create_ai_client() -> AIClient:
    """Factory: create AIClient from environment variables."""
    api_key = os.getenv("AI_ENGINE_API_KEY")
    if not api_key:
        raise ValueError("AI_ENGINE_API_KEY environment variable is not set")
    base_url = os.getenv("AI_ENGINE_BASE_URL")
    if not base_url:
        raise ValueError("AI_ENGINE_BASE_URL environment variable is not set")
    return AIClient(api_key=api_key, base_url=base_url)
