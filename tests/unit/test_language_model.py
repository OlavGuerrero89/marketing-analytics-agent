"""Unit tests for the OpenRouter language-model factory."""

from unittest.mock import patch

import pytest

from app.adapters.language_model import LanguageModelFactory
from app.config import Settings
from app.domain.exceptions import LanguageModelConfigurationError


def test_rejects_missing_openrouter_api_key() -> None:
    settings = Settings(
        openrouter_api_key=None,
        _env_file=None,
    )

    with pytest.raises(
        LanguageModelConfigurationError,
        match="OPENROUTER_API_KEY is required",
    ):
        LanguageModelFactory.create(settings)


@patch("app.adapters.language_model.ChatOpenAI")
def test_builds_chat_model_with_openrouter_configuration(
    chat_openai_mock,
) -> None:
    expected_model = object()
    chat_openai_mock.return_value = expected_model
    settings = Settings(
        openrouter_api_key="test-key",
        openrouter_model="openrouter/free",
        openrouter_base_url="https://openrouter.ai/api/v1",
        llm_temperature=0.0,
        llm_timeout_seconds=30.0,
        _env_file=None,
    )

    model = LanguageModelFactory.create(settings)

    assert model is expected_model

    configuration = chat_openai_mock.call_args.kwargs
    assert configuration["api_key"].get_secret_value() == "test-key"
    assert configuration["base_url"] == "https://openrouter.ai/api/v1"
    assert configuration["model"] == "openrouter/free"
    assert configuration["temperature"] == 0.0
    assert configuration["timeout"] == 30.0
    assert configuration["max_retries"] == 2