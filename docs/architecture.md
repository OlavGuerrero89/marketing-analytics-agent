# Architecture

## Objective

The solution is a small analytical agent that answers a deliberately narrow set of natural-language questions about marketing performance.

The main architectural constraint is grounding: every factual value in an answer must come from the governed Cube semantic layer. The agent never queries ClickHouse directly and does not rely on the language model to calculate or invent results.

## System Context

```
flowchart LR
    User[CLI user] --> Agent[Marketing analytics agent]
    Agent --> OpenRouter[OpenRouter free model router]
    Agent --> Cube[Cube semantic layer]
    Cube --> ClickHouse[ClickHouse warehouse]
    Agent --> Langfuse[Langfuse observability]
```

## Runtime Flow

```
flowchart TD
    Start([Question]) --> Interpret[Interpret intent]

    Interpret -->|Ready| Query[Build and execute Cube query]
    Interpret -->|Ambiguous or unsupported| Direct[Return controlled message]
    Interpret -->|Model failure| Error[Return controlled error]

    Query -->|Rows returned| Validate[Validate Cube result]
    Query -->|Cube failure| Error

    Validate -->|Valid| Answer[Compose grounded answer]
    Validate -->|Invalid| Error

    Answer --> End([Final response])
    Direct --> End
    Error --> End
```

## Component Responsibilities

### Command-Line Interface

`app/cli.py` is the composition root and user interface.

It:

- Reads the question.
- Loads validated settings.
- Creates the language model and optional Langfuse integration.
- Creates the Cube client and application services.
- Builds and invokes the LangGraph workflow.
- Prints the final response.
- Converts known configuration failures into controlled exit codes.

The CLI contains no analytical business logic.

### Intent Parser

`app/services/intent_parser.py` translates natural language into an `AnalyticalRequest`.

The output is constrained by a Pydantic schema containing only supported:

- Metrics.
- Dimensions.
- Date ranges.
- Time granularities.
- Sorting instructions.
- Result limits.

The model cannot return SQL or arbitrary Cube member names.

Small deterministic rules handle critical canonical inputs:

- Empty input requests a question.
- “Most purchases” maps to purchase ranking.
- “Best” without an explicit metric requests clarification.

These rules improve consistency when OpenRouter changes the free underlying model. They do not contain campaign names, numerical results, or expected answers.

### Domain Models

`app/domain/models.py` defines the technology-independent analytical contract.

Validation includes:

- At least one metric.
- Complete date ranges.
- Chronologically valid dates.
- No duplicate metrics or dimensions.
- Time granularity only when dates are present.
- Ordering only by a requested metric.
- Valid status-specific intent payloads.

The domain request does not contain Cube syntax. This keeps business intent separate from infrastructure.

### Query Builder

`app/services/query_builder.py` is the only component that translates a validated analytical request into Cube member names.

It:

- Uses a fixed public view.
- Maps allowlisted metrics and dimensions.
- Adds date ranges and granularity.
- Adds sorting and limits.
- Produces a deterministic Cube JSON query.

It does not accept raw SQL or arbitrary field names from the language model.

### Cube Client

`app/adapters/cube_client.py` is the HTTP adapter for Cube.

It:

- Calls Cube’s load endpoint.
- Applies the configured timeout.
- Supports an optional API token.
- Distinguishes transport, HTTP, and response-shape failures.
- Returns raw Cube rows to the validation layer.

This adapter is the agent’s exclusive data interface.

### Result Validator

`app/services/result_validator.py` treats external data as untrusted.

Before answer generation, it verifies:

- The Cube response contains only expected members.
- Required dimensions and metrics are present.
- Dimension values have valid shapes.
- Numeric values can be represented as finite decimals.
- Null values are accepted only where appropriate.
- The response corresponds to the original analytical request.

The answer composer never receives unvalidated Cube data.

### Answer Composer

`app/services/answer_composer.py` produces deterministic factual answers.

It:

- States the requested period or full available period.
- Formats monetary values, counts, and ratios.
- Handles empty results.
- Handles null derived metrics.
- Supports only known response shapes.

The language model does not rewrite or embellish the final numerical answer. This limits conversational flexibility but reduces hallucination risk.

### LangGraph Workflow

`app/graph/workflow.py` makes the execution flow explicit.

The nodes are:

1. `interpret`
2. `query`
3. `validate`
4. `answer`
5. `direct_response`
6. `error_response`

Routing is based on validated graph state:

- Ready intents continue to Cube.
- Clarification and unsupported intents bypass Cube.
- Known failures terminate through a controlled error response.

Each node has a narrow responsibility and receives its dependencies from the composition root.

## Warehouse Design

The ClickHouse model separates campaign attributes from daily performance facts.

### Campaign Dimension

`marketing.campaigns` contains one record per campaign.

The campaign identifier is the ordering key.

### Daily Performance Fact

`marketing.campaign_performance_daily` uses one campaign and one active date as its logical grain.

The table is:

- Partitioned by event month.
- Ordered by event date and campaign.
- Constrained against negative monetary values.
- Constrained so clicks cannot exceed impressions.

This structure supports aggregation by campaign, channel, objective, and period without introducing unnecessary user-level detail.

## Fake Data Generation

`warehouse/seed/generate_data.py` creates a deterministic dataset using random seed `42`.

The generator includes:

- Eight campaigns.
- Four marketing channels.
- Multiple objectives.
- Different campaign active periods.
- Daily volume variation.
- Weekend effects.
- Campaign-specific response rates.
- A controlled performance improvement for one campaign.
- A controlled zero-purchase period for another campaign.

The generator validates the grain, ranges, relationships, dates, campaign references, and expected record count before writing CSV files.

The data is intentionally synthetic and does not represent real customers.

## Cube Design

The base cubes are private:

- `campaigns`
- `campaign_performance`

The public analytical contract is the `marketing_performance` view.

This prevents the agent from depending on implementation details of raw Cube models and provides a single allowlisted surface for queries.

Cube owns the definitions of derived measures such as CTR, CPC, CPA, and ROAS. The agent consumes those definitions instead of independently recalculating them.

## LLM Boundary

The model is used for semantic interpretation, where natural-language flexibility is valuable.

The model is not trusted to control:

- SQL.
- Raw warehouse access.
- Arbitrary Cube members.
- Mathematical calculations.
- Returned data types.
- Final factual values.
- Error-handling policy.

This boundary combines probabilistic language understanding with deterministic analytical execution.

## Observability

Langfuse is optional for local execution but enabled when both keys are provided.

A traced request includes:

- The original question.
- Model interpretation.
- LangGraph execution.
- Query-node activity containing the Cube operation.
- Validation and answer nodes.
- The final response.

Credentials are loaded from environment variables and are not included in trace inputs or outputs.

## Error Strategy

Known failures are translated into safe user-facing responses.

Examples include:

- Model response validation failure.
- OpenRouter request failure.
- Cube transport or HTTP failure.
- Invalid Cube response structure.
- Missing result data.
- Unsupported answer shape.
- Ambiguous or unsupported requests.

The current implementation returns concise messages rather than exposing stack traces or internal service details.

## SOLID Application

The design follows SOLID principles pragmatically:

- **Single responsibility:** parsing, querying, validation, and composition are separate.
- **Open/closed:** new supported intents can be added through new metric mappings and answer strategies without replacing external adapters.
- **Liskov substitution:** the workflow depends on a Cube data-source protocol, enabling controlled test doubles.
- **Interface segregation:** the query node requires only the `load` operation.
- **Dependency inversion:** the composition root injects adapters and services into graph-node factories.

The project avoids creating abstractions that do not support a current boundary or test.

## Key Tradeoffs

### Determinism over conversational breadth

Only three analytical intents are supported. This produces predictable and testable behavior but is not a general-purpose marketing assistant.

### CLI over a web interface

The CLI reduces surface area and allows reviewers to focus on the analytical architecture. An API could later reuse the same services and graph.

### Aggregate facts over user-level events

Daily campaign data is sufficient for the requested analysis but cannot support customer journeys, cohorts, or multi-touch attribution.

### Free routed inference

The required OpenRouter free router may change its underlying model. Structured output, schema validation, tests, and deterministic intent guards reduce—but do not eliminate—this variability.

### Local demonstration credentials

The included credentials are suitable only for a local mock environment. They are not a production security model.

## Production Improvements

Before production use, the system should add:

- A dedicated read-only ClickHouse identity for Cube.
- Managed secret storage and rotation.
- API authentication and authorization.
- Tenant and data-access isolation.
- Encrypted internal traffic.
- Retriable operations with backoff and circuit breaking.
- Idempotent ingestion.
- Data freshness and quality monitoring.
- Model evaluation and prompt regression datasets.
- Semantic-model and data-contract versioning.
- Cost, latency, and reliability monitoring.
- Deployment rollback and disaster-recovery procedures.
- Privacy, audit, and retention controls.
- A broader intent catalog introduced only with governed metrics and tests.

