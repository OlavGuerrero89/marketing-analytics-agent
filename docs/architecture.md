# Architecture

## Approved decisions

- A CLI is used instead of a web interface.
- Cube is the agent's exclusive data interface.
- The warehouse has a campaign dimension and a daily campaign-performance fact table.
- The public semantic contract is the `marketing_performance` view.
- The language model interprets questions and explains validated results.
- Deterministic code controls validation, query construction, calculations, and errors.
- No embeddings or vector database are included.
- Langfuse Cloud and OpenRouter are external services.
- The solution is an assessment demonstration, not a production deployment.

## Workflow

Interpret, validate, query Cube, validate results, and compose a grounded answer.
