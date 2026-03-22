"""Tests for AI client service."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from services.ai_client import (
    AIClient,
    AIClientError,
    ModelConfig,
    get_model_config,
    MODEL_CONFIGS,
    create_ai_client,
)


class TestModelConfig:
    def test_kimi_k25_config_exists(self):
        config = get_model_config("gpt-oss-120b")
        assert isinstance(config, ModelConfig)
        assert config.display_name == "GPT-OSS 120B"
        assert config.max_tokens == 4096
        assert config.temperature == 0.3
        assert config.max_input_chars == 8000
        assert config.json_forced is True

    def test_unknown_model_raises_key_error(self):
        with pytest.raises(KeyError):
            get_model_config("nonexistent-model")


class TestAIClientInit:
    @patch("services.ai_client.AsyncOpenAI")
    def test_creates_client_with_configured_params(self, mock_openai_cls):
        client = AIClient(api_key="test-key", base_url="https://api.test.com")
        mock_openai_cls.assert_called_once_with(
            api_key="test-key",
            base_url="https://api.test.com",
            timeout=60.0,
        )

    def test_create_ai_client_missing_api_key_raises(self, monkeypatch):
        monkeypatch.delenv("AI_ENGINE_API_KEY", raising=False)
        monkeypatch.setenv("AI_ENGINE_BASE_URL", "https://api.test.com")
        with pytest.raises(ValueError, match="AI_ENGINE_API_KEY"):
            create_ai_client()

    def test_create_ai_client_missing_base_url_raises(self, monkeypatch):
        monkeypatch.setenv("AI_ENGINE_API_KEY", "test-key")
        monkeypatch.delenv("AI_ENGINE_BASE_URL", raising=False)
        with pytest.raises(ValueError, match="AI_ENGINE_BASE_URL"):
            create_ai_client()

    @patch("services.ai_client.AsyncOpenAI")
    def test_create_ai_client_from_env(self, mock_openai_cls, monkeypatch):
        monkeypatch.setenv("AI_ENGINE_API_KEY", "env-key")
        monkeypatch.setenv("AI_ENGINE_BASE_URL", "https://api.env.com")
        client = create_ai_client()
        mock_openai_cls.assert_called_once_with(
            api_key="env-key",
            base_url="https://api.env.com",
            timeout=60.0,
        )


class TestComplete:
    @pytest.mark.asyncio
    @patch("services.ai_client.AsyncOpenAI")
    async def test_returns_response_text(self, mock_openai_cls):
        mock_message = MagicMock()
        mock_message.content = "校正済みテキスト"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_cls.return_value = mock_client

        client = AIClient(api_key="test-key", base_url="https://api.test.com")
        result = await client.complete(
            model="gpt-oss-120b",
            system_prompt="system prompt",
            user_prompt="user prompt",
            max_tokens=4096,
            temperature=0.3,
            request_id="test-request-123",
        )

        assert result == "校正済みテキスト"

    @pytest.mark.asyncio
    @patch("services.ai_client.AsyncOpenAI")
    async def test_returns_empty_string_when_content_is_none(self, mock_openai_cls):
        mock_message = MagicMock()
        mock_message.content = None
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_cls.return_value = mock_client

        client = AIClient(api_key="test-key", base_url="https://api.test.com")
        result = await client.complete(
            model="gpt-oss-120b",
            system_prompt="system",
            user_prompt="user",
            max_tokens=4096,
            temperature=0.3,
            request_id="test-request",
        )

        assert result == ""

    @pytest.mark.asyncio
    @patch("services.ai_client.AsyncOpenAI")
    async def test_passes_correct_parameters_to_openai(self, mock_openai_cls):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="text"))]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_cls.return_value = mock_client

        client = AIClient(api_key="test-key", base_url="https://api.test.com")
        await client.complete(
            model="gpt-oss-120b",
            system_prompt="sys",
            user_prompt="usr",
            max_tokens=2048,
            temperature=0.5,
            request_id="req-1",
        )

        mock_client.chat.completions.create.assert_called_once_with(
            model="gpt-oss-120b",
            messages=[
                {"role": "system", "content": "sys"},
                {"role": "user", "content": "usr"},
            ],
            max_tokens=2048,
            temperature=0.5,
        )

    @pytest.mark.asyncio
    @patch("services.ai_client.AsyncOpenAI")
    async def test_empty_choices_raises_ai_invalid_response(self, mock_openai_cls):
        mock_response = MagicMock()
        mock_response.choices = []

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_cls.return_value = mock_client

        client = AIClient(api_key="test-key", base_url="https://api.test.com")
        with pytest.raises(AIClientError) as exc_info:
            await client.complete(
                model="gpt-oss-120b",
                system_prompt="s",
                user_prompt="u",
                max_tokens=4096,
                temperature=0.3,
                request_id="req-empty",
            )

        assert exc_info.value.error_code == "ai_invalid_response"

    @pytest.mark.asyncio
    @patch("services.ai_client.AsyncOpenAI")
    async def test_unexpected_error_raises_ai_invalid_response(self, mock_openai_cls):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=RuntimeError("unexpected SDK bug")
        )
        mock_openai_cls.return_value = mock_client

        client = AIClient(api_key="test-key", base_url="https://api.test.com")
        with pytest.raises(AIClientError) as exc_info:
            await client.complete(
                model="gpt-oss-120b",
                system_prompt="s",
                user_prompt="u",
                max_tokens=4096,
                temperature=0.3,
                request_id="req-unexpected",
            )

        assert exc_info.value.error_code == "ai_invalid_response"

    @pytest.mark.asyncio
    @patch("services.ai_client.AsyncOpenAI")
    async def test_timeout_raises_ai_timeout_error(self, mock_openai_cls):
        import openai

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=openai.APITimeoutError(request=MagicMock())
        )
        mock_openai_cls.return_value = mock_client

        client = AIClient(api_key="test-key", base_url="https://api.test.com")
        with pytest.raises(AIClientError) as exc_info:
            await client.complete(
                model="gpt-oss-120b", system_prompt="s", user_prompt="u",
                max_tokens=4096, temperature=0.3, request_id="req-timeout",
            )
        assert exc_info.value.error_code == "ai_timeout"

    @pytest.mark.asyncio
    @patch("services.ai_client.AsyncOpenAI")
    async def test_rate_limit_raises_ai_rate_limit_error(self, mock_openai_cls):
        import openai

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=openai.RateLimitError(
                message="Rate limit",
                response=MagicMock(status_code=429),
                body=None,
            )
        )
        mock_openai_cls.return_value = mock_client

        client = AIClient(api_key="test-key", base_url="https://api.test.com")
        with pytest.raises(AIClientError) as exc_info:
            await client.complete(
                model="gpt-oss-120b", system_prompt="s", user_prompt="u",
                max_tokens=4096, temperature=0.3, request_id="req-rate",
            )
        assert exc_info.value.error_code == "ai_rate_limit"

    @pytest.mark.asyncio
    @patch("services.ai_client.AsyncOpenAI")
    async def test_api_status_error_raises_ai_invalid_response(self, mock_openai_cls):
        import openai

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=openai.APIStatusError(
                message="Server error",
                response=MagicMock(status_code=500),
                body=None,
            )
        )
        mock_openai_cls.return_value = mock_client

        client = AIClient(api_key="test-key", base_url="https://api.test.com")
        with pytest.raises(AIClientError) as exc_info:
            await client.complete(
                model="gpt-oss-120b", system_prompt="s", user_prompt="u",
                max_tokens=4096, temperature=0.3, request_id="req-api",
            )
        assert exc_info.value.error_code == "ai_invalid_response"

    @pytest.mark.asyncio
    @patch("services.ai_client.AsyncOpenAI")
    async def test_connection_error_raises_ai_invalid_response(self, mock_openai_cls):
        import openai

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=openai.APIConnectionError(request=MagicMock())
        )
        mock_openai_cls.return_value = mock_client

        client = AIClient(api_key="test-key", base_url="https://api.test.com")
        with pytest.raises(AIClientError) as exc_info:
            await client.complete(
                model="gpt-oss-120b", system_prompt="s", user_prompt="u",
                max_tokens=4096, temperature=0.3, request_id="req-conn",
            )
        assert exc_info.value.error_code == "ai_invalid_response"
