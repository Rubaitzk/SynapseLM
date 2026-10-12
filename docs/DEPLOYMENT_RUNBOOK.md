# SynapseLM Production Deployment Runbook

This runbook contains the exact step-by-step instructions for deploying SynapseLM to production.

---

## Prerequisites Before You Begin

1. A **Railway** account ([railway.com](https://railway.com)).
2. A **Vercel** account ([vercel.com](https://vercel.com)).
3. Access to the Git repository containing SynapseLM.
4. Python 3.10+ locally to generate required encryption and authentication secrets.

---

## Pre-Deployment: Generate Secure Production Keys

Run the following commands in your local terminal or Python environment to generate the necessary cryptographic secrets. **Save these securely in a password manager:**

```bash
# 1. Generate JWT SECRET_KEY (64-character random hex string)
python -c "import secrets; print(secrets.token_hex(32))"

# 2. Generate CREDENTIAL_ENCRYPTION_KEY (Fernet URL-safe 32-byte base64 key)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

> [!CAUTION]
> **Key Permanence**: The `CREDENTIAL_ENCRYPTION_KEY` is used to encrypt and decrypt users' personal LLM API keys. Once set in production, **never change or delete this key**. If changed, all previously saved user API keys become permanently unreadable.

---

## Stage 1: Railway Project Setup

1. Log in to [Railway Dashboard](https://railway.com/dashboard).
2. Click **New Project**.
3. Select **Empty Project** (or name it `synapselm-production`).

---

## Stage 2: Provision Managed PostgreSQL

1. Inside your Railway project, click **+ Create** or **+ New**.
2. Select **Database** -> **Add PostgreSQL**.
3. Railway provisions a persistent PostgreSQL service (default service name: `Postgres`).
4. Click on the PostgreSQL service card, navigate to the **Variables** tab, and note the variable reference:
   - `${{Postgres.DATABASE_URL}}` (or internal connection string `postgresql://postgres:...@postgres.railway.internal:5432/railway`).
   - *Note: SynapseLM automatically normalizes `postgres://` to `postgresql://`.*
5. Under the **Settings** tab, verify that the database is private (do not add a public TCP proxy domain unless specifically required for external database inspection).

---

## Stage 3: Provision Managed Redis

1. Inside the same Railway project, click **+ Create** or **+ New**.
2. Select **Database** -> **Add Redis**.
3. Railway provisions a Redis 7+ service (default service name: `Redis`).
4. Click on the Redis service card, navigate to the **Variables** tab, and note the variable reference:
   - `${{Redis.REDIS_URL}}` (or internal connection string `redis://default:...@redis.railway.internal:6379`).
5. Under the **Settings** tab, verify that Redis remains internal within Railway's private network.

---

## Stage 4: Deploy the Backend Service on Railway

1. Inside the Railway project, click **+ Create** or **+ New** -> **GitHub Repo**.
2. Select your `SynapseLM` repository.
3. Once the service card appears, click on it and navigate to the **Settings** tab:
   - **Service Name**: Rename to `synapselm-backend`.
   - **Root Directory**: Leave blank (root `/`) or set to `/backend`.
     - *If blank*: Railway uses the root `railway.json` and `backend/Dockerfile`.
     - *If `/backend`*: Railway uses `backend/railway.json` and `backend/Dockerfile`.
   - **Build**: Builder will automatically detect Dockerfile (`backend/Dockerfile`).
   - **Networking**: Click **Generate Domain** under *Public Networking*. Railway will assign a public HTTPS domain such as `https://synapselm-backend-production.up.railway.app`. Note this domain.
4. Navigate to the **Variables** tab and add the environment variables described in Stage 5.

---

## Stage 5: Configure Backend Environment Variables

In the **Variables** tab of the `synapselm-backend` service, add the following variables:

| Variable Name | Value / Railway Reference | Description |
|---|---|---|
| `ENVIRONMENT` | `production` | Enables production mode checks |
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` | Connects directly via Railway private network |
| `REDIS_URL` | `${{Redis.REDIS_URL}}` | Connects directly via Railway private network |
| `SECRET_KEY` | *(Your generated 64-char hex key from Pre-Deployment)* | Signs and verifies user JWT tokens |
| `ALGORITHM` | `HS256` | JWT signature algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | 24-hour token validity |
| `CREDENTIAL_ENCRYPTION_KEY` | *(Your generated Fernet base64 key from Pre-Deployment)* | Symmetric encryption for BYOK credentials |
| `ALLOWED_ORIGINS` | `https://your-frontend-project.vercel.app` *(update once Vercel domain is assigned)* | Allowed CORS origins for browser security |
| `LLM_PROVIDER` | `gemini` | Default AI provider (`gemini` or `openai`) |
| `LLM_MODEL` | `gemini-3.6-flash` | Default AI model name |
| `LLM_API_KEY` | *(Optional system-wide API key)* | Fallback key if users have not entered personal keys |

---

## Stage 6: Database Migrations

SynapseLM uses Alembic for schema migrations. Railway handles this through the configured `preDeployCommand`:

1. In `railway.json`, `preDeployCommand: "alembic upgrade head"` is already configured.
2. During every deploy, Railway runs migrations once in a dedicated release container before starting the web server.
3. To manually run or verify migrations via the Railway CLI:
   ```bash
   # Link your local repo to the Railway project
   railway link
   
   # Run migrations on the remote production database
   railway run alembic upgrade head
   ```
4. Verify the current revision matches `590e4e31ede3`:
   ```bash
   railway run alembic current
   ```

---

## Stage 7 & 8: Verify Backend Health & Infrastructure Connectivity

Once Railway completes the deployment, test both health endpoints using curl or your browser:

### 1. Verify Liveness Probe
```bash
curl -i https://<your-backend-domain>.up.railway.app/health
```
**Expected Response:**
```json
HTTP/1.1 200 OK
{"status": "ok", "service": "SynapseLM API"}
```

### 2. Verify Readiness Probe (PostgreSQL & Redis Connectivity)
```bash
curl -i https://<your-backend-domain>.up.railway.app/health/ready
```
**Expected Response:**
```json
HTTP/1.1 200 OK
{"status": "ready", "database": "ok", "redis": "ok", "service": "SynapseLM API"}
```
> [!NOTE]
> If `database` or `redis` returns an error, the endpoint responds with `HTTP 503 Service Unavailable`. Check the service environment variables and private network status.

---

## Stage 9: Configure and Deploy the Vercel Frontend

1. Log in to [Vercel Dashboard](https://vercel.com/dashboard).
2. Click **Add New...** -> **Project**.
3. Import your `SynapseLM` Git repository.
4. Configure Project Settings:
   - **Framework Preset**: `Vite`
   - **Root Directory**: Click *Edit* and select `frontend`.
   - **Build Command**: `npm run build` (or leave default).
   - **Output Directory**: `dist` (or leave default).
   - **Install Command**: `npm install` (or leave default).

---

## Stage 10: Configure Frontend Environment Variables

Before clicking Deploy, expand the **Environment Variables** section in Vercel:

| Variable Name | Example Production Value | Description |
|---|---|---|
| `VITE_API_BASE_URL` | `https://<your-backend-domain>.up.railway.app/api` | REST API URL (**must include `/api`**) |
| `VITE_WS_BASE_URL` | `wss://<your-backend-domain>.up.railway.app` | WebSocket URL (**must use `wss://`**) |

Click **Deploy**. Vercel will install dependencies, compile the TypeScript/React application, and assign a production URL (e.g., `https://synapselm.vercel.app`).

### Update Backend CORS
Return to your Railway backend service -> **Variables** tab:
Update `ALLOWED_ORIGINS` to include your new Vercel domain:
```
ALLOWED_ORIGINS=https://synapselm.vercel.app
```
Railway will automatically redeploy the backend with the new CORS origin.

---

## Stage 11 - 14: End-to-End Application Smoke Testing

Open `https://synapselm.vercel.app` in your browser and verify the full workflow:

### 1. Authentication
- Register a new account (`/register`).
- Log out and log back in (`/login`).
- Refresh the page while logged in to confirm session persistence via JWT.

### 2. Personal LLM Credentials & Conversation
- Navigate to **Settings** (`/settings`).
- Enter your personal Gemini or OpenAI API key and save.
- Create a new conversation (`/conversations/new` or `/`).
- Send a message. Confirm AI streaming response is received.

### 3. Conversation Sharing
- Open the conversation menu and click **Share**.
- Generate a share link (e.g., with 24h expiration or no expiration).
- Copy the share link URL (`https://synapselm.vercel.app/shares/<token>`).

### 4. Branching & Access Requests
- Open an incognito window or second browser and log in as a second user.
- Paste the share link.
- Click **Branch Conversation**: Confirm an isolated branch conversation is created with full context snapshot up to the share point.
- Click **Request Access**: Confirm collaboration request is dispatched.

### 5. Access Request Approval & Real-Time Notifications
- In the owner's browser window, verify the incoming request toast and sidebar badge.
- Click **Accept Request**:
  - Verify that the second user immediately receives an `Approved` banner and toast notification via WebSocket.
  - Verify that the second user is added to the conversation participants.

### 6. Real-Time Multi-Session Chat
- Place the owner and collaborator windows side-by-side.
- Send a message from User A: Confirm User B sees the message appear in real-time without refreshing.
- Send a message from User B: Confirm User A sees typing indicators and incoming messages in real-time.

---

## Stage 15: Operational Procedures & Diagnostics

### Viewing Logs
- **Railway Backend**: Click on `synapselm-backend` -> **Deployments** -> select active deployment -> **View Logs**.
- **Railway Database / Redis**: Click on service -> **Deployments** -> **View Logs**.
- **Vercel Frontend**: Click on your project -> **Logs** or **Analytics**.

### Diagnosing Common Failures

| Symptom | Probable Cause | Remedy |
|---|---|---|
| CORS Error in browser console (`Access-Control-Allow-Origin`) | `ALLOWED_ORIGINS` in Railway does not match Vercel URL | Verify `ALLOWED_ORIGINS` in Railway matches exact Vercel URL (protocol `https://`, no trailing slash). |
| WebSocket connection failed (`1008` or handshake error) | `VITE_WS_BASE_URL` wrong or token expired | Ensure `VITE_WS_BASE_URL` uses `wss://` protocol pointing to the Railway domain. Re-login if token expired. |
| HTTP 503 on `/health/ready` | PostgreSQL or Redis unreachable | Verify `DATABASE_URL` and `REDIS_URL` in Railway Variables tab. Check if DB services are active. |
| Decryption error when sending message | `CREDENTIAL_ENCRYPTION_KEY` changed or missing | Ensure `CREDENTIAL_ENCRYPTION_KEY` matches the key used when saving user credentials. |
| 404 on page refresh on Vercel | Missing SPA rewrite | Verify `frontend/vercel.json` exists in repo with `/index.html` rewrites. |

### Database Backup & Recovery
- **Railway Automated Backups**: In Railway, open the PostgreSQL service -> **Backups** tab. Railway provides automated daily backups and point-in-time recovery.
- **Manual Backup (pg_dump)**:
  ```bash
  railway run pg_dump -Fc > backup_$(date +%Y%m%d_%H%M%S).dump
  ```
- **Manual Restore**:
  ```bash
  railway run pg_restore -d railway backup_file.dump
  ```

### Rollback Procedure
1. **Frontend**: In Vercel, go to **Deployments**, find the previous stable deployment, click the three dots (`...`), and select **Promote to Production**.
2. **Backend**: In Railway, go to `synapselm-backend` -> **Deployments**, click on the previous stable deployment, and click **Rollback**.
3. **Database**: If a schema rollback is required, run `railway run alembic downgrade -1` only after ensuring downstream data compatibility.
