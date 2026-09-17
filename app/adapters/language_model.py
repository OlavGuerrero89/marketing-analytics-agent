"""Language-model adapter configured for OpenRouter."""

from langchain_openai import ChatOpenAI

from app.config import Settings
from app.domain.exceptions import LanguageModelConfigurationError


class LanguageModelFactory:
    """Create the configured LangChain chat model."""

    @staticmethod
    def create(settings: Settings) -> ChatOpenAI:
        api_key = settings.openrouter_api_key

        if api_key is None or not api_key.get_secret_value().strip():
            raise LanguageModelConfigurationError(
                "OPENROUTER_API_KEY is required to use the language model."
            )

        return ChatOpenAI(
            api_key=api_key,
            base_url=settings.openrouter_base_url,
            model=settings.openrouter_model,
            temperature=settings.llm_temperature,
            timeout=settings.llm_timeout_seconds,
            max_retries=2,
        )
