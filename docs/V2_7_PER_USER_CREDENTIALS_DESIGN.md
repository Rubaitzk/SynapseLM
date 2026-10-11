# SynapseLM V2.7: Secure Per-User Provider Credentials Design

## 1. Credential Ownership and Access Control
- **Domain Model**: Introduce a `UserCredential` entity owned exclusively by the `User`.
  - Fields: `id`, `user_id`, `provider_name` (e.g., 'gemini', 'openai'), `encrypted_api_key`, `key_version`, `created_at`, `updated_at`.
  - **Constraint**: There must be a unique database constraint on `(user_id, provider_name)` to prevent duplicate credentials for the same user and provider.
- **Access Control**: A user can only view metadata (not the raw key), update, or delete their own credentials. Team owners and system admins cannot access or use a member's personal API keys for unrelated workloads.

## 2. Encrypted Storage and Key-Management Strategy
- **Encryption Scheme**: Raw API keys are never stored in plaintext. They are encrypted symmetrically using Fernet authenticated encryption (`cryptography.fernet`).
- **Master Key**: A system-level `CREDENTIAL_ENCRYPTION_KEY` environment variable acts as the root of trust, kept strictly outside the database and source control. It is explicitly separate from the provider API key (`LLM_API_KEY`).
- **Missing Key Behavior**: If `CREDENTIAL_ENCRYPTION_KEY` is missing, the application must fail safely at startup or during credential operations. It must *never* silently store plaintext keys if the encryption configuration is unavailable.
- **Key Versioning**: `key_version` stores an identifier for the master key version to support rotation.

## 3. Create, Update, Validate, and Delete Operations
- **Create/Update**: The frontend submits the raw API key. The backend encrypts it immediately in memory, stores the ciphertext, and drops the raw key.
- **Validate**: The backend makes a lightweight check to the provider (e.g., listing models) using the provided key before saving it. If validation fails, the key is *not* saved, and the failure is explained to the user. The application will not silently substitute another provider.
- **Delete (Revocation)**: Users can revoke a key at any time, which hard-deletes the row, ensuring the deleted credential cannot be used in future requests.
- **Caching**: No in-memory credential cache will be introduced unless strictly necessary. If one exists, it must be safely invalidated upon update or deletion of the credential.

## 4. Secret Redaction and Error Response Contracts
- **API Responses**: Responses only include safe metadata: `id`, `provider_name`, `is_configured: bool`, `created_at`, `updated_at`. Never return plaintext or ciphertext key material.
- **Error Responses**: Structured machine-readable errors. Sensitive provider error details (which might contain secrets) must be redacted.
- **Logging**: Do not log plaintext credentials, ciphertext, request bodies containing keys, or sensitive provider errors. Decrypt credentials only when needed for an authorized provider operation.

## 5. Credential Resolution When Generating Responses
The `orchestrator.py` module integrates credential resolution without duplicating provider initialization logic:
1. **Per-User Credential**: If the user executing the action (sending the message) has a configured key for the conversation's explicitly selected `ai_provider` and model, use it.
2. **System Fallback**: If no personal credential exists, apply the explicitly configured system-fallback policy (using `LLM_API_KEY`), if permitted.
3. **Failure**: If no permitted credential is available, return the existing structured provider-configuration error.
4. **Initialization**: Initialize the provider with the resolved credential and the exact supported model. Do not silently change the selected provider or model.

## 6. Behavior in Shared Conversations
- **Execution Context**: AI generation executes under the context of the authenticated user *sending the message*, not the conversation owner or the person who originally created the share.
- **Missing Credentials**: If Bob sends a message in Alice's shared conversation but has no personal key, Bob's request fails immediately (if system fallback is unavailable/disabled). Alice's key is never utilized for Bob's actions.

## 7. Backward Compatibility
- The `LLM_API_KEY` environment variable remains functional for deployments explicitly permitting system fallback.
- Existing offline tests relying on `LLM_API_KEY` patching will continue to pass without modification.
- Single-tenant or hobbyist deployments can continue operating purely on the system `.env` key.

## 8. Safe Migration Strategy & Security Tests
- **Database Migration**: A focused Alembic migration creates the `user_credentials` table. No existing data needs to move.
- **Security Tests**:
  - Test that fetching credential metadata never leaks the ciphertext or plaintext key.
  - Test that Bob cannot send a message using Alice's credential in a shared chat.
  - Test that attempting to use a revoked credential falls back to the system key or fails.
  - Test that symmetric encryption behaves securely (round-trip correctness, tampered ciphertext rejection, and missing key handling). Do not assert that encrypting the same input twice yields identical ciphertext (Fernet is non-deterministic).

## 9. Key Management & Deferred Rotation Limitation
- **Master Key Format**: `CREDENTIAL_ENCRYPTION_KEY` must be a 32-byte url-safe base64-encoded string (generated via `Fernet.generate_key().decode()`).
- **Storage Separation**: Stored exclusively in server environment variables or deployment secrets managers; never checked into version control or written into the database.
- **Key Loss/Modification**: If `CREDENTIAL_ENCRYPTION_KEY` is lost or changed without migration, existing ciphertexts cannot be decrypted. The backend raises a controlled `decryption_failed` error, requiring users to re-enter their API keys.
- **Deferred Key Rotation Limitation**: Automated multi-key rotation is deferred to a future maintenance phase. When implemented, key rotation will be performed by:
  1. Booting with both old and new keys in memory.
  2. Querying all `user_credentials` rows with `key_version = "v1"`.
  3. Decrypting each row with the old key and re-encrypting with the new key.
  4. Updating `key_version` to `"v2"`.
  5. Retiring the old key from the deployment environment.
