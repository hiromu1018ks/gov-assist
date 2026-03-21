# AI Client Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the AI client service that calls the SAKURA AI Engine via its OpenAI-compatible API with 60-second timeout and structured error handling.

**Architecture:** A thin async wrapper around the `openai` Python SDK (`AsyncOpenAI`), configured via environment variables (`AI_ENGINE_API_KEY`, `AI_ENGINE_BASE_URL`). Raises typed `AIClientError` exceptions with error codes (`ai_timeout`, `ai_rate_limit`, `ai_invalid_response`) that the proofread router (Task 9) will catch and convert to HTTP responses. Model configuration is defined as a frozen dataclass dict (`MODEL_CONFIGS`) for use by the models router (Task 8).

**Tech Stack:** `openai>=1.0.0` (AsyncOpenAI), `pytest-asyncio>=0.23`

**Design spec reference:** §4.1 (AI Engine connection), §4.2 (model config table), §5.5 (error codes: `ai_timeout`, `ai_rate_limit`, `ai_invalid_response`), §9.2 (logging: ERROR level with request_id/endpoint/status_code/model)

---

## Files

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/requirements.txt` | Modify | Add `openai>=1.0.0`, `pytest-asyncio>=0.23` |
| `backend/.env.example` | Modify | Add `AI_ENGINE_BASE_URL` |
| `backend/services/ai_client.py` | Create | `AIClient` class, `ModelConfig` dataclass, `AIClientError`, `create_ai_client()` factory, `MODEL_CONFIGS` |
| `backend/tests/test_ai_client.py` | Create | Unit tests for model config, client init, completion, and error handling |

---

### Task 1: Dependencies & Configuration

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/.env.example`

- [ ] **Step 1: Add openai SDK to requirements.txt**

Append to `backend/requirements.txt`:
```
openai>=1.0.0
pytest-asyncio>=0.23
```

- [ ] **Step 2: Add AI_ENGINE_BASE_URL to .env.example**

The current `.env.example` has:
```
AI_ENGINE_API_KEY=your-api-key-here
```

Add after it:
```
AI_ENGINE_BASE_URL=https://api.ai.sakura.ad.jp/v1
```

- [ ] **Step 3: Install dependencies**

Run:
```bash
cd backend && pip install -r requirements.txt
```

- [ ] **Step 4: Verify openai is importable**

Run: `cd backend && python -c "import openai; print(openai.__version__)"`

Expected: Version string printed (e.g. `1.x.x`)

- [ ] **Step 5: Commit**

```bash
git add backend/requirements.txt backend/.env.example
git commit -m "chore: add openai SDK and AI_ENGINE_BASE_URL config for Task 4"
```

---

### Task 2: AIClient Core — Model Config & Class Structure

**Files:**
- Create: `backend/services/ai_client.py`
- Create: `backend/tests/test_ai_client.py`

- [ ] **Step 1: Write failing tests for model config and client initialization**

Create `backend/tests/test_ai_client.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_ai_client.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'services.ai_client'`

- [ ] **Step 3: Implement model config and AIClient class skeleton**

Create `backend/services/ai_client.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_ai_client.py -v`

Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/ai_client.py backend/tests/test_ai_client.py
git commit -m "feat(backend): add AIClient skeleton with model config and factory"
```

---

### Task 3: AI Completion — Happy Path

**Files:**
- Modify: `backend/services/ai_client.py` (replace `raise NotImplementedError` in `complete()`)
- Modify: `backend/tests/test_ai_client.py` (add `TestComplete` class)

- [ ] **Step 1: Write failing tests for complete() method**

Add to `backend/tests/test_ai_client.py`:

```python
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
            model="kimi-k2.5",
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
            model="kimi-k2.5",
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
            model="kimi-k2.5",
            system_prompt="sys",
            user_prompt="usr",
            max_tokens=2048,
            temperature=0.5,
            request_id="req-1",
        )

        mock_client.chat.completions.create.assert_called_once_with(
            model="kimi-k2.5",
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
                model="kimi-k2.5",
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
                model="kimi-k2.5",
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
                model="kimi-k2.5", system_prompt="s", user_prompt="u",
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
                model="kimi-k2.5", system_prompt="s", user_prompt="u",
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
                model="kimi-k2.5", system_prompt="s", user_prompt="u",
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
                model="kimi-k2.5", system_prompt="s", user_prompt="u",
                max_tokens=4096, temperature=0.3, request_id="req-conn",
            )
        assert exc_info.value.error_code == "ai_invalid_response"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_ai_client.py::TestComplete -v`

Expected: FAIL with `NotImplementedError`

- [ ] **Step 3: Implement complete() method**

Replace `raise NotImplementedError` in `complete()` with:

```python
        try:
            response = await self._client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_ai_client.py::TestComplete -v`

Expected: All 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/ai_client.py backend/tests/test_ai_client.py
git commit -m "feat(backend): implement AIClient.complete() with error handling"
```

---

### Task 4: Full Test Suite Verification

**Files:** None (verification only)

- [ ] **Step 1: Run new AI client tests**

Run: `cd backend && python -m pytest tests/test_ai_client.py -v`

Expected: All 15 tests PASS (2 model config + 4 init + 9 complete including error handling)

- [ ] **Step 2: Run entire test suite to check for regressions**

Run: `cd backend && python -m pytest -v`

Expected: All tests PASS (existing tests + 15 new AI client tests)

- [ ] **Step 3: Final commit (only if fixes were needed)**

```bash
git add backend/services/ai_client.py backend/tests/test_ai_client.py
git commit -m "fix: resolve test regressions from AI client addition"
```

Skip this step if no fixes were needed.
