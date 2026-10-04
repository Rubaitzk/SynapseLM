# Security

- **Authentication**: Token/session-based. Passwords securely hashed.
- **Authorization**: Enforced server-side for every protected resource.
- **Secrets**: Managed through environment variables, never committed. Provide `.env.example`.
- **API Protection**: Safe CORS, reasonable request limits, no sensitive info in logs.
