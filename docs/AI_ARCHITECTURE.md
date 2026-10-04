# AI Architecture

Backend is responsible for constructing AI context. Frontend must NEVER directly call the LLM provider.

## Flow
`Message Service` -> `Conversation Context Service` -> `AI Orchestrator` -> `LLM Provider Interface` -> `Concrete LLM Provider`

## LLM Provider Abstraction
An abstraction with operations for:
- generating responses
- streaming responses
- exposing capabilities

The concrete provider must be replaceable.
