"""Natural-language interpretation using a structured LLM response."""

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from app.domain.exceptions import LanguageModelResponseError
from app.domain.models import (
    IntentStatus,
    InterpretedQuestion,
)

SYSTEM_PROMPT = """
You interpret marketing analytics questions.

Supported business questions:
1. Marketing spend grouped by channel.
2. Campaigns ranked by purchases.
3. Campaigns ranked by ROAS, defined as revenue divided by spend.

Rules:
- Use only the metrics and dimensions allowed by the response schema.
- Never generate SQL, Cube member names, or database fields.
- "Strongest result relative to spend" means ROAS.
- "Most purchases" means purchases ordered descending with limit 1.
- A ranking without dates uses the complete available data period.
- Never invent dates that were not supplied by the user.
- If "best" or "strongest" has no explicit metric or definition, request
  clarification.
- Questions comparing periods or requesting unsupported analysis must use
  the unsupported status.
- A ready response contains a request and no message.
- A clarification or unsupported response contains a concise message and
  no request.
""".strip()


class IntentParser:
    """Convert a user question into a validated analytical request."""

    def __init__(self, model: BaseChatModel) -> None:
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_PROMPT),
                ("human", "{question}"),
            ]
        )
        structured_model = model.with_structured_output(
            InterpretedQuestion,
            method="json_schema",
        )
        self._chain = prompt | structured_model

    def parse(self, question: str) -> InterpretedQuestion:
        normalized_question = question.strip()

        if not normalized_question:
            return InterpretedQuestion(
                status=IntentStatus.NEEDS_CLARIFICATION,
                message="Please provide a marketing analytics question.",
            )

        result = self._chain.invoke(
            {"question": normalized_question}
        )

        if not isinstance(result, InterpretedQuestion):
            raise LanguageModelResponseError(
                "The language model returned an invalid interpretation."
            )

        return result