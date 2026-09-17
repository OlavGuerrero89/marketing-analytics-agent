# Marketing Analytics Agent

A small, production-minded analytical agent that answers natural-language questions about marketing performance. The agent retrieves governed metrics exclusively through Cube, backed by a mock ClickHouse warehouse.

The implementation favors correctness, explicit control flow, validation, and traceability over a broad conversational scope.

## Supported Questions

The current version supports three analytical intents:

1. Marketing spend grouped by channel for a selected period.
  ```
  How much did we spend by channel from January 1 to January 31, 2026?
  ```
2. Campaign ranked by total purchases.
  ```
  Which campaign generated the most purchases?
  ```
3. Campaign ranked by return on advertising spend.
  ```
  Which campaign had the strongest result relative to spend?
  ```

When no dates are supplied, the agent explicitly states that it used the full available data period.

An ambiguous question such as:

```
Which campaign performed best?
```

does not trigger a data query. The agent asks whether “best” should mean purchases or ROAS.

Period-over-period comparisons and metrics outside the documented semantic contract are intentionally unsupported.

## Architecture

```
flowchart LR
    U[CLI user] --> I[Intent interpretation]
    I --> G[LangGraph workflow]
    G --> Q[Deterministic query builder]
    Q --> C[Cube semantic layer]
    C --> H[ClickHouse warehouse]
    C --> V[Result validator]
    V --> A[Deterministic answer composer]
    A --> U
    G -. traces .-> L[Langfuse]
    I -. OpenRouter free model .-> O[LLM inference]
```

### Components

- **ClickHouse** stores the mock campaign dimension and daily campaign-performance facts.
- **Cube** is the exclusive analytical data interface used by the agent.
- **LangChain** provides prompt composition and structured model output.
- **LangGraph** implements the explicit interpret, query, validate, and answer flow.
- **OpenRouter Free Models Router** provides inference without a paid fallback.
- **Langfuse** records the model interaction, graph execution, semantic-layer operation, and final answer.
- **Pydantic** validates configuration and the structured analytical request.
- **Docker Compose** provides a reproducible local environment.
- **Poetry** manages Python dependencies and packaging.

The agent never sends SQL to ClickHouse and never allows the language model to construct raw Cube member names.

## Repository Structure

```
app/
  adapters/       External integrations for Cube and the language model
  domain/         Metrics, dimensions, validated models, and exceptions
  graph/          LangGraph state, nodes, routing, and workflow assembly
  services/       Query construction, result validation, and answer composition

cube/
  model/cubes/    Private Cube models
  model/views/    Public governed semantic view

warehouse/
  init/           ClickHouse schema initialization
  seed/           Deterministic generator and generated CSV datasets

tests/
  unit/           Deterministic component and workflow tests
  integration/    Live Cube and complete workflow integration tests

docs/             Architecture, metrics, AI disclosure, and video notes
```

## Data Model

The warehouse uses a small star-like model.

### `marketing.campaigns`

One row per campaign:

- `campaign_id`
- `campaign_name`
- `channel`
- `objective`
- `start_date`
- `end_date`

### `marketing.campaign_performance_daily`

One row per campaign and active date:

- `event_date`
- `campaign_id`
- `impressions`
- `clicks`
- `spend`
- `purchases`
- `revenue`

The fact table is partitioned monthly and ordered by date and campaign identifier.

The dataset contains eight campaigns and 436 daily performance rows covering January and February 2026. It is generated with random seed `42`, making it deterministic and reproducible.

The generator validates:

- Unique campaign identifiers.
- Valid campaign date ranges.
- Unique campaign-date fact grain.
- Nonnegative counts and monetary values.
- `clicks <= impressions`.
- `purchases <= clicks`.
- Fact dates within the campaign active period.
- The expected number of generated records.

## Cube Semantic Layer

The private Cube models are:

- `campaigns`
- `campaign_performance`

The agent is restricted to the public `marketing_performance` view.

### Measures

- `impressions`
- `clicks`
- `spend`
- `purchases`
- `revenue`
- `ctr`
- `cpc`
- `cpa`
- `roas`

### Dimensions

- `campaign_id`
- `campaign_name`
- `channel`
- `objective`
- `event_date`

The semantic layer centralizes metric definitions and prevents the agent from directly querying raw warehouse tables.

## Metric Definitions


| Metric      | Definition                       |
| ----------- | -------------------------------- |
| Impressions | Sum of served ad impressions     |
| Clicks      | Sum of ad clicks                 |
| Spend       | Sum of advertising spend in USD  |
| Purchases   | Sum of attributed purchases      |
| Revenue     | Sum of attributed revenue in USD |
| CTR         | Clicks divided by impressions    |
| CPC         | Spend divided by clicks          |
| CPA         | Spend divided by purchases       |
| ROAS        | Revenue divided by spend         |


Division-based metrics return null when their denominator is zero.

Additional details are available in `docs/metrics.md`.

## LangGraph Workflow

The workflow uses explicit nodes with narrow responsibilities:

1. **Interpret** converts the natural-language question into a validated, technology-independent analytical request.
2. **Query** converts that request into a governed Cube query and calls the Cube API.
3. **Validate** confirms that the returned dimensions, measures, and values match the request.
4. **Answer** renders validated values into a deterministic response.
5. **Direct response** returns clarification or unsupported-scope messages without querying Cube.
6. **Error response** converts known model, Cube, or validation failures into controlled user-facing messages.

Routing decisions are based on validated state rather than unconstrained model output.

## LLM and Deterministic Logic Boundary

The language model is responsible only for interpreting supported natural-language questions into a structured schema.

Deterministic application code controls:

- The metric and dimension allowlists.
- Date and request validation.
- Cube member construction.
- Sort direction and result limits.
- Cube response validation.
- Metric formatting.
- Final factual answer composition.
- Error and clarification behavior.

The final numerical answer is not generated from the model’s memory. It is composed from values retrieved through Cube.

Small deterministic guards handle canonical phrases such as “most purchases” and ambiguous phrases such as “best campaign.” These guards stabilize important behavior when the free model router changes the underlying model. They do not contain campaign names or expected analytical values.

## Setup

### Prerequisites

- Docker Desktop with Docker Compose.
- An OpenRouter API key.
- Optional Langfuse project keys for tracing.
- Python 3.12 and Poetry 2.4 for local development and tests.

### 1. Configure the environment

Copy the example file:

```
cp .env.example .env
```

Set at least:

```
OPENROUTER_API_KEY=your_openrouter_key
```

For tracing, also configure both:

```
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
LANGFUSE_SECRET_KEY=your_langfuse_secret_key
```

Do not commit `.env`.

The configured model must remain:

```
OPENROUTER_MODEL=openrouter/free
```

No paid model or paid fallback is used.

### 2. Start ClickHouse and Cube

```
docker compose up -d clickhouse cube
```

Check service health:

```
docker compose ps
```

Both services should report `healthy`.

On a fresh ClickHouse volume, the scripts mounted from `warehouse/init` create the database and tables automatically.

### 3. Load the deterministic mock data

The committed CSV files can be loaded directly.

```
docker compose exec -T clickhouse sh -c \
  'clickhouse-client \
  --user "$CLICKHOUSE_USER" \
  --password "$CLICKHOUSE_PASSWORD" \
  --async_insert=0 \
  --query "INSERT INTO marketing.campaigns FORMAT CSVWithNames"' \
  < warehouse/seed/campaigns.csv
```

```
docker compose exec -T clickhouse sh -c \
  'clickhouse-client \
  --user "$CLICKHOUSE_USER" \
  --password "$CLICKHOUSE_PASSWORD" \
  --async_insert=0 \
  --query "INSERT INTO marketing.campaign_performance_daily FORMAT CSVWithNames"' \
  < warehouse/seed/campaign_performance_daily.csv
```

Load the seed files once for a fresh volume. The tables intentionally do not perform automatic deduplication.

Verify the row counts:

```
docker compose exec clickhouse sh -c \
  'clickhouse-client \
  --user "$CLICKHOUSE_USER" \
  --password "$CLICKHOUSE_PASSWORD" \
  --query "
    SELECT table, total_rows
    FROM system.tables
    WHERE database = '\''marketing'\''
    ORDER BY table
  "'
```

Expected counts:

```
campaign_performance_daily    436
campaigns                       8
```

To regenerate the same CSV files using seed `42`:

```
poetry run python warehouse/seed/generate_data.py
```

### 4. Run the agent in Docker

Build the image:

```
docker compose --profile agent build agent
```

Ask a question:

```
docker compose run --rm agent \
  "Which campaign generated the most purchases?"
```

Another example:

```
docker compose run --rm agent \
  "How much did we spend by channel from January 1 to January 31, 2026?"
```

Ambiguous-case example:

```
docker compose run --rm agent \
  "Which campaign performed best?"
```

## Local Development

Create the Poetry environment and install development dependencies:

```
poetry env use 3.12
poetry install --extras dev
```

Because a locally executed agent reaches Cube through the published host port, override the container URL:

```
CUBE_API_URL=http://localhost:4000/cubejs-api/v1 \
poetry run marketing-agent \
  "Which campaign generated the most purchases?"
```

## Tests and Quality Controls

Run static checks:

```
poetry run ruff check .
```

Run the complete test suite against the local Cube service:

```
CUBE_API_URL=http://localhost:4000/cubejs-api/v1 \
poetry run pytest
```

Run tests with branch coverage:

```
CUBE_API_URL=http://localhost:4000/cubejs-api/v1 \
poetry run pytest \
  --cov=app \
  --cov-report=term-missing \
  --cov-report=xml
```

The repository enforces a minimum coverage threshold of 80%. At the time of submission, the suite passes with coverage above that threshold.

The tests include:

- Query construction.
- Cube client behavior and errors.
- Structured intent interpretation.
- Domain validation.
- Result validation.
- Answer composition.
- LangGraph routing and node behavior.
- CLI behavior.
- Live Cube aggregation.
- A complete workflow integration test.
- Ambiguous and imperfect cases.

The integration tests require healthy local ClickHouse and Cube containers.

## Observability

When both Langfuse keys are configured, each request creates a trace containing:

- The root agent request.
- The model interaction.
- LangGraph execution and nodes.
- The Cube semantic-query operation.
- Validation and answer steps.
- The final response.

Tracing is optional for local execution. If neither Langfuse key is provided, the agent runs without tracing. Providing only one key is treated as a configuration error.

Secrets are loaded from environment variables and are not added to trace input or output.

## Error and Imperfect-Input Handling

The agent does not invent an answer when the request or data is imperfect.

It provides controlled behavior for:

- Empty questions.
- Ambiguous ranking criteria.
- Unsupported analyses.
- Invalid structured model output.
- OpenRouter failures.
- Cube transport and response errors.
- Missing Cube results.
- Unexpected members or invalid values.
- Empty datasets.
- Zero denominators in derived metrics.

## Assumptions

- Spend and revenue are denominated in USD.
- Purchases and revenue are already attributed to a campaign.
- The mock data does not model attribution windows or multi-touch attribution.
- A missing date range means the complete available period.
- “Result relative to spend” means ROAS.
- Campaign-date is the fact-table grain.
- The generated data is illustrative and does not represent real customers or campaigns.
- The assessment runs as a local demonstration rather than a production deployment.

## Tradeoffs and Deliberate Scope

### CLI instead of a web application

A CLI keeps the interface reproducible and directs attention to analytical correctness and architecture. A production system could expose the same application services through an authenticated API.

### Narrow intent catalog

The agent supports three useful analytical questions rather than arbitrary analytics. This makes the semantic and validation contract explicit and testable.

### Deterministic final answers

The model interprets language, but deterministic code formats factual responses. This reduces hallucination risk at the cost of supporting fewer response shapes.

### No vector database or embeddings

The task operates on structured analytical data. Cube is the appropriate retrieval interface; semantic document retrieval would add complexity without improving the required answers.

### Generated aggregate data

The warehouse contains daily campaign facts rather than user-level events. This is sufficient for the selected metrics but cannot answer customer attribution or cohort questions.

### Local credentials

The example ClickHouse account is suitable only for local demonstration. A production deployment should give Cube a dedicated read-only identity with narrowly scoped permissions.

## Production Improvements

Before production use, I would add:

- A read-only Cube warehouse identity and managed secret storage.
- Authentication, authorization, and tenant isolation.
- Network policies and encrypted service communication.
- Persistent LangGraph checkpointing where conversational state is required.
- Rate limiting, retries with backoff, and circuit breakers.
- Stronger model evaluation datasets and regression tests.
- Semantic-model versioning and data-contract checks.
- Freshness, completeness, and anomaly monitoring.
- Idempotent ingestion and orchestration.
- Deployment health, readiness, and rollback controls.
- Cost, latency, and model-quality monitoring.
- Explicit privacy and retention policies.
- More supported intents only after adding corresponding governed metrics and tests.

## AI Usage Disclosure

AI-assisted vibe coding was used to help interpret the assessment, propose architecture and code, troubleshoot errors, and improve documentation. Every proposed change was reviewed incrementally, executed under human supervision, and verified using static analysis, automated tests, integration tests, live analytical queries, Docker execution, and Langfuse traces. No AI-generated output was accepted solely on the basis that it looked plausible.

Further disclosure is available in `docs/ai_usage.md`.

## Video Walkthrough

The walkthrough link and coverage checklist are maintained in `docs/video_walkthrough.md`.