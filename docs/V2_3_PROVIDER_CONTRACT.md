# V2.3 Provider and Model Selection Contract

This document outlines the technical design for resolving LLM providers and models across SynapseLM, ensuring determinism, error visibility, and extensibility for future user-specific configurations.

## 1. Explicit Model Selection

The system must strictly adhere to the user's explicit model choices.

- **Persistence**: The intended provider (`ai_provider`) and model (`ai_model`) must be persisted with the conversation (`Conversation` row).
- **Defaults**: Environment variables (`LLM_PROVIDER`, `LLM_MODEL`) serve exclusively as fallback defaults when the request omits an explicit selection.
- **Validation**: The backend must validate the selected provider and model combination against a predefined list of supported configurations (e.g., `gemini` with `gemini-1.5-flash`, `mock` with `mock`).
- **Rejection**: The system must reject unknown providers, unsupported models, and invalid provider/model combinations.
- **No Silent Substitution**: The backend must *never* silently substitute a provider or model. If the requested configuration is invalid or unachievable, it must explicitly fail.

## 2. Separate Model Resolution from Credential Resolution

Model resolution and credential resolution are distinct processes.

- **Independent Resolution**: The provider/model pair chosen for the conversation dictates *what* to run. The credentials dictate *how* it is authenticated.
- **Configuration Defaults**: The current `.env` configuration serves as the development/system default.
- **Extension Point**: A clean extension point will be defined for future per-user credentials. The orchestrator will attempt to look up appropriate credentials before falling back to the system `.env` defaults. (Storage of these user credentials is not implemented in this phase).

## 3. Shared Conversations

When users collaborate in shared conversations, strict credential boundaries must be maintained.

- **Preservation of Rules**: Existing ownership, sharing, branch, and access-request authorization rules remain unchanged.
- **No Credential Exposure**: One user's credentials must never be exposed to collaborators.
- **Collaborator Execution**: When a collaborator sends a message in a conversation configured for a specific provider, the backend resolves the credentials based on the conversation owner or the configured applicable credentials, not the collaborator's personal credentials (unless explicitly designed otherwise in the future).
- **Failure Mode**: If the applicable credential is unavailable (e.g., owner has no key configured for the conversation's provider), the system must return a configuration-required error response. It must *never* silently switch models or use a fallback provider.

## 4. Structured Errors

The application must return consistent, machine-readable HTTP errors rather than generic 500 errors or silent fallbacks.

All provider and credential-related errors will use appropriate 4xx HTTP status codes and return a JSON payload with a specific `error_code`, `provider`, and `detail`.

- `provider_configuration_missing` (HTTP 400 Bad Request): Required credentials for the resolved provider are missing.
- `invalid_provider_model_combo` (HTTP 400 Bad Request): The requested provider and model combination is unsupported or unknown.
- `unsupported_provider` (HTTP 400 Bad Request): The requested provider is unknown or not supported by the system.
- `invalid_credentials` (HTTP 401 Unauthorized): The resolved credentials were rejected by the external provider API.
- `rate_limit_exceeded` (HTTP 429 Too Many Requests): The external provider's rate limits have been exceeded.
- `authorization_error` (HTTP 403 Forbidden): The caller does not have permission to use the selected configuration or credentials.

Example payload for `provider_configuration_missing`:
```json
{
  "error_code": "provider_configuration_missing",
  "provider": "gemini",
  "detail": "Gemini API key is required but not configured."
}
```

## 5. Security Extension Points

Future implementations will build upon this contract to provide:
- **Secure Credential Persistence**: Encrypted storage of user API keys via `user_credentials` or a `UserLLMCredentials` table.
- **Credential Isolation**: Guaranteeing that a key bound to a user cannot be decrypted or utilized outside of authorized contexts.
- **Revocation**: Mechanisms for users to instantly revoke keys stored in the system.
