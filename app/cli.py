"""Command-line interface and application composition root."""

import argparse
from collections.abc import Sequence

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

from app.adapters.cube_client import CubeClient
from app.adapters.language_model import LanguageModelFactory
from app.config import Settings
from app.domain.exceptions import LanguageModelConfigurationError
from app.graph.workflow import build_workflow
from app.services.answer_composer import AnswerComposer
from app.services.intent_parser import IntentParser
from app.services.query_builder import CubeQueryBuilder
from app.services.result_validator import ResultValidator


def create_argument_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Ask grounded questions about marketing performance."
        )
    )
    parser.add_argument(
        "question",
        nargs="*",
        help="Natural-language marketing analytics question.",
    )
    return parser


def create_observability(
    settings: Settings,
) -> tuple[Langfuse | None, CallbackHandler | None]:
    """Create optional Langfuse tracing components."""
    public_key = settings.langfuse_public_key
    secret_key = settings.langfuse_secret_key

    if public_key is None and secret_key is None:
        return None, None

    if public_key is None or secret_key is None:
        raise ValueError(
            "Both LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY "
            "must be configured together."
        )

    public_value = public_key.get_secret_value()
    client = Langfuse(
        public_key=public_value,
        secret_key=secret_key.get_secret_value(),
        base_url=settings.langfuse_base_url,
    )
    handler = CallbackHandler(public_key=public_value)

    return client, handler


def run_agent(question: str, settings: Settings) -> str:
    """Build and execute one complete agent request."""
    model = LanguageModelFactory.create(settings)
    parser = IntentParser(model)
    langfuse_client, langfuse_handler = create_observability(
        settings
    )

    with CubeClient(
        base_url=settings.cube_api_url,
        timeout_seconds=settings.request_timeout_seconds,
        token=settings.cube_api_token,
    ) as cube_client:
        workflow = build_workflow(
            parser=parser,
            data_source=cube_client,
            query_builder=CubeQueryBuilder(),
            result_validator=ResultValidator(),
            answer_composer=AnswerComposer(),
        )

        config = None

        if langfuse_handler is not None:
            config = {
                "callbacks": [langfuse_handler],
                "run_name": "marketing-analytics-agent",
            }

        if langfuse_client is None:
            result = workflow.invoke(
                {"question": question},
                config=config,
            )
        else:
            with langfuse_client.start_as_current_observation(
                as_type="span",
                name="marketing-analytics-request",
                input={"question": question},
            ) as observation:
                result = workflow.invoke(
                    {"question": question},
                    config=config,
                )
                observation.update(
                    output={"answer": result.get("answer")}
                )

            langfuse_client.flush()

    return result.get(
        "answer",
        "The agent completed without producing an answer.",
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line application."""
    arguments = create_argument_parser().parse_args(argv)
    question = " ".join(arguments.question).strip()

    if not question:
        question = input("Question: ").strip()

    settings = Settings()

    try:
        answer = run_agent(question, settings)
    except LanguageModelConfigurationError as error:
        print(f"Configuration error: {error}")
        return 2
    except ValueError as error:
        print(f"Configuration error: {error}")
        return 2

    print(answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())