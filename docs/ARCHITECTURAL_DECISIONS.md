# Architectural Decisions

1. **Modular Monolith**: Chose modular monolith over microservices for V1 to reduce operational complexity while maintaining clean separation of concerns.
2. **PostgreSQL as Source of Truth**: Postgres will store all durable domain state.
3. **Redis for Ephemeral State**: WebSockets presence, typing, etc. will utilize Redis. Redis will not store persistent domain entities.
4. **LLM Abstraction**: AI features will sit behind an orchestrator interface so providers can be swapped easily.
5. **Project Name**: SynapseLM.
