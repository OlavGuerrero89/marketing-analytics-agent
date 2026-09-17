# AI Usage Disclosure

## Development Assistance

I used OpenAI Codex as an AI-assisted coding partner while developing this assessment.

The development process followed a supervised vibe-coding approach:

1. I interpreted the business and technical requirements.
2. Codex proposed architecture, implementation templates, tests, and troubleshooting steps.
3. I reviewed each proposal before incorporating it.
4. I requested corrections when a proposal did not match the intended architecture or observed behavior.
5. I executed the commands and inspected the resulting behavior.
6. Changes were accepted only after verification.

Some explicitly approved configuration changes were applied directly by the assistant, then reviewed and validated by me.

I did not treat AI-generated output as correct merely because it was syntactically plausible.

## How the Output Was Reviewed

The implementation was reviewed through:

- Incremental inspection of each proposed file.
- Ruff static analysis.
- Unit tests for domain models, adapters, services, graph nodes, workflow behavior, and the CLI.
- Branch-aware test coverage with an enforced minimum threshold of 80%.
- Integration tests against the running Cube service.
- A complete workflow integration test using live Cube data.
- Direct comparison of agent answers with governed analytical results.
- Docker image construction and container execution.
- Inspection of Langfuse traces.
- Validation of ambiguous and imperfect-input behavior.
- Verification that secrets and runtime data are excluded from version control and the Docker image.

At the time of final documentation, the automated suite passes with coverage above the enforced threshold.

## Runtime AI Usage

The application itself uses the OpenRouter Free Models Router:

```
openrouter/free
```

No paid model and no paid fallback are configured.

The runtime model is used only to interpret supported natural-language questions into a constrained Pydantic schema.

It is not trusted to:

- Generate SQL.
- Select arbitrary Cube members.
- Query ClickHouse directly.
- Calculate analytical results.
- Invent missing data.
- Produce the final numerical answer.

Deterministic application code builds Cube queries, validates returned data, formats values, handles errors, and composes factual answers.

## Human Decisions

The following decisions remained under human control:

- The supported business questions.
- Warehouse grain and schema.
- Fake-data assumptions.
- Cube measures and dimensions.
- The public semantic contract.
- LangGraph state and node boundaries.
- LLM and deterministic-code responsibilities.
- Validation and error-handling policy.
- Testing scope and coverage threshold.
- Docker and local execution strategy.
- Architectural tradeoffs and production recommendations.

## Limitations of AI Assistance

AI assistance can produce incorrect APIs, outdated syntax, invalid assumptions, or implementations that appear reasonable without satisfying the business requirement.

For that reason, generated suggestions were checked against:

- The assessment instructions.
- The installed library versions.
- Actual service behavior.
- Automated tests.
- Live Cube results.
- Docker execution.
- Observability traces.

The final submission reflects my reviewed technical decisions and my understanding of the implementation.