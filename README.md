# Marketing Analytics Agent

A small analytics agent that answers natural-language questions about marketing
performance using Cube as its exclusive data interface.

## Status

Work in progress. Components will be implemented and verified incrementally.

## Architecture

- ClickHouse: mock analytical warehouse
- Cube: governed semantic layer
- LangChain: model and tool integration
- LangGraph: explicit workflow
- Langfuse: execution tracing
- OpenRouter Free Models Router: model inference

## Supported Questions

To be documented after the semantic model and tests are implemented.

## Quick Start

To be documented after the local environment is verified.

## Documentation

- Architecture: `docs/architecture.md`
- Metric definitions: `docs/metrics.md`
- AI usage disclosure: `docs/ai_usage.md`
- Video walkthrough: `docs/video_walkthrough.md`
