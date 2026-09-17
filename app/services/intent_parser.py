"""Natural-language interpretation using a structured LLM response."""

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from openai import OpenAIError
from pydantic import ValidationError

from app.domain.exceptions import LanguageModelResponseError
from app.domain.metrics import Dimension, Metric, SortDirection
from app.domain.models import (
    AnalyticalRequest,
    IntentStatus,
    InterpretedQuestion,
    SortSpec,
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

Status decision rules:
- Use needs_clarification when the question could become supported after the
  user specifies a missing metric, date, or definition.
- Example: "Which campaign performed best?" requires clarification because
  "best" could mean most purchases or highest ROAS.
- Use unsupported only when clarification cannot make the request fit the
  supported scope.
- Example: comparing January with February is unsupported because period
  comparison is outside the current scope.
- Never label a question as unsupported when your message asks the user to
  clarify a missing choice.
""".strip()


class IntentParser:
    """Convert a user question into a validated analytical request."""
    PURCHASE_RANKING_TERMS = ("most", "highest", "top")
    AMBIGUOUS_RANKING_TERMS = ("best", "strongest")
    EXPLICIT_METRIC_TERMS = (
        "spend",
        "purchase",
        "revenue",
        "roas",
        "ctr",
        "cpc",
        "cpa",
        "click",
        "impression",
        "relative to spend",
    )

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

        normalized_lower = normalized_question.casefold()
        
        asks_for_purchase_ranking = (
            "purchas" in normalized_lower
            and any(
                term in normalized_lower
                for term in self.PURCHASE_RANKING_TERMS
            )
        )

        if asks_for_purchase_ranking:
            return InterpretedQuestion(
                status=IntentStatus.READY,
                request=AnalyticalRequest(
                    metrics=(Metric.PURCHASES,),
                    dimensions=(Dimension.CAMPAIGN_NAME,),
                    order_by=SortSpec(
                        metric=Metric.PURCHASES,
                        direction=SortDirection.DESCENDING,
                    ),
                    limit=1,
                ),
            )

        has_ambiguous_ranking = any(
            term in normalized_lower
            for term in self.AMBIGUOUS_RANKING_TERMS
        )
        has_explicit_metric = any(
            term in normalized_lower
            for term in self.EXPLICIT_METRIC_TERMS
        )

        if has_ambiguous_ranking and not has_explicit_metric:
            return InterpretedQuestion(
                status=IntentStatus.NEEDS_CLARIFICATION,
                message=(
                    "Which metric should define best performance: "
                    "purchases or ROAS?"
                ),
            )

        try:
            result = self._chain.invoke(
                {"question": normalized_question}
            )
        except ValidationError as error:
            raise LanguageModelResponseError(
                "The language model returned data that violates "
                "the analytical request schema."
            ) from error
        
        except OpenAIError as error:
            raise LanguageModelResponseError(
                "The language model request failed."
            ) from error

        if not isinstance(result, InterpretedQuestion):
            raise LanguageModelResponseError(
                "The language model returned an invalid interpretation."
            )

        return result