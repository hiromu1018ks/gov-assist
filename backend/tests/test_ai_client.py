"""Tests for AI client service."""

import pytest
from unittest.mock import patch, MagicMock

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
        config = get_model_config("kimi-k2.5")
        assert isinstance(config, ModelConfig)
        assert config.display_name == "Kimi K2.5"
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
