# SynapseLM Production Deployment Guide (V2.10)

This guide provides complete, production-grade instructions for deploying SynapseLM without guessing or relying on development-mode defaults.

---

## 1. Architecture Overview

SynapseLM consists of four core runtime components:

1. **Frontend (SPA)**:
   - React 19 + TypeScript + Vite + Tailwind CSS.
   - Built to static HTML/JS/CSS assets (`frontend/dist/`).
   - Served via NGINX, Caddy, or static cloud hosting (e.g., Cloudflare Pages, AWS S3/CloudFront, Vercel).
2. **Backend API (REST + WebSockets)**:
   - FastAPI running under Python 3.10+ ASGI server (`uvicorn`).
   - Handles authentication, conversations, branching, access requests, per-user credential encryption, and LLM orchestration.
   - Entry point: `app.main:app`.
3. **Database (PostgreSQL)**:
   - PostgreSQL 14+ database storing users, teams, conversations, branches, messages, shares, access requests, and encrypted API credentials.
   - Schema state managed via linear Alembic migrations (`backend/alembic/`).
4. **Realtime Pub/Sub (Redis)**:
   - Redis 6.0+ instance.
   - Provides multi-worker message fan-out and presence synchronization over `conversation:*` pub/sub channels.

```
                    ┌────────────────────────┐
                    │      Client Browser    │
                    └───────────┬────────────┘
                                │ HTTPS / WSS
                                ▼
                    ┌────────────────────────┐
                    │  Reverse Proxy (NGINX) │
                    └─────┬────────────┬─────┘
           Static Assets  │            │ /api and /ws
                          ▼            ▼
                 ┌─────────────┐  ┌───────────────────────┐
                 │  Vite Dist  │  │  FastAPI (Uvicorn)   │
                 └─────────────┘  └───┬───────────────┬───┘
                                      │               │
                                      ▼               ▼
                              ┌───────────────┐ ┌───────────┐
                              │  PostgreSQL   │ │   Redis   │
                              └───────────────┘ └───────────┘
```

### Why this architecture fits SynapseLM
- **Single-host or modular deployment**: A modest single Linux VPS (e.g., 2 vCPU, 4GB RAM) running NGINX, Uvicorn, PostgreSQL, and Redis easily handles thousands of active sessions with negligible operational overhead.
- **WebSocket sticky-connection free**: Because FastAPI workers publish events to Redis pub/sub and subscribe to `conversation:*`, any worker can broadcast to any client connection, enabling horizontal scaling without sticky sessions.
- **Credential isolation**: Encrypted user API keys are safely decrypted in-memory per request using `CREDENTIAL_ENCRYPTION_KEY`, avoiding disk persistence of plaintext keys.

---

## 2. Infrastructure Prerequisites

Before deploying, ensure you have:

- **Server / Compute**:
  - Minimum: 2 vCPU, 4 GB RAM, 20 GB SSD (Ubuntu 22.04 LTS or Debian 12 recommended).
  - Alternatives: PaaS deployment (Render, Fly.io, Railway, or AWS ECS/Fargate).
- **Domain & DNS**:
  - A registered domain name (e.g., `synapselm.example.com`).
  - DNS `A` or `CNAME` records pointing to your server's public IP address.
- **Managed or Local Services**:
  - PostgreSQL 14+ instance.
  - Redis 6.0+ instance.
- **System Packages** (for Ubuntu/Debian host):
  - `python3.10` or higher, `python3-pip`, `python3-venv`
  - `nodejs` (v20+) and `npm`
  - `nginx`
  - `certbot` and `python3-certbot-nginx`

---

## 3. Production Environment Variables Reference

SynapseLM uses environment variables loaded from the shell environment or a secure `.env` file.

### Backend Environment Variables (`backend/.env`)

| Variable | Required? | Secret? | Format / Placeholder | Purpose | Restart Required? |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `DATABASE_URL` | **Yes** | **Yes** | `postgresql://user:password@host:5432/synapselm` | PostgreSQL connection string | Yes |
| `SECRET_KEY` | **Yes** | **Yes** | 64+ char random hex string | JWT signing key | Yes (invalidates active sessions if changed) |
| `ALGORITHM` | No | No | `HS256` | JWT signature algorithm (default: `HS256`) | Yes |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | No | `1440` (24h) or `43200` (30d) | Session token lifetime in minutes | Yes |
| `CREDENTIAL_ENCRYPTION_KEY` | **Yes** | **CRITICAL** | 32-byte URL-safe base64 string | AES-GCM Fernet key for encrypting user LLM keys | Yes (**Do not lose!**) |
| `REDIS_URL` | **Yes** | Optional | `redis://[:password@]host:6379/0` | Redis connection for WebSocket Pub/Sub | Yes |
| `ALLOWED_ORIGINS` | **Yes** | No | `https://synapselm.example.com` | Comma-separated allowed CORS origins | Yes |
| `LLM_PROVIDER` | No | No | `gemini` or `openai` or `mock` | Default LLM provider for new chats | Yes |
| `LLM_MODEL` | No | No | `gemini-3.6-flash` or `gpt-4o` | Default model for conversations | Yes |
| `LLM_API_KEY` | Optional | **Yes** | `AIzaSy...` or `sk-...` | Fallback system key if user has no personal key | Yes |

> [!CAUTION]
> **Preserving `CREDENTIAL_ENCRYPTION_KEY`**:
> User API credentials saved in the database are encrypted using this key. If this key is lost, existing user credentials **cannot be decrypted** and will raise `Decryption failed` errors until users re-enter them in Settings. Back up this key in a secure secrets manager (e.g., Vault, AWS Secrets Manager, 1Password) independent of database backups.

### Frontend Environment Variables (`frontend/.env`)

| Variable | Required? | Secret? | Format / Placeholder | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `VITE_API_BASE_URL` | No* | No | `https://api.synapselm.example.com/api` | API Base URL (leave empty if using reverse proxy `/api`) |
| `VITE_WS_BASE_URL` | No* | No | `wss://api.synapselm.example.com` | WebSocket Base URL (leave empty if using reverse proxy `/ws`) |

*\* When deploying frontend and backend under the same domain via NGINX, both frontend variables can be left empty.*

---

## 4. Step-by-Step Deployment Instructions

### Step 1: Clone Repository and Prepare Virtual Environments

```bash
# Clone the repository
git clone https://github.com/your-org/SynapseLM.git /var/www/synapselm
cd /var/www/synapselm

# Create backend Python virtual environment
cd /var/www/synapselm/backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 2: Generate Production Secrets

Run the following commands on your server to generate cryptographically secure secrets:

```bash
# 1. Generate JWT SECRET_KEY (64 characters)
python3 -c "import secrets; print(secrets.token_hex(32))"

# 2. Generate CREDENTIAL_ENCRYPTION_KEY (Fernet 32-byte url-safe base64)
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Save these values securely and populate `/var/www/synapselm/backend/.env`:

```ini
DATABASE_URL=postgresql://synapse_user:SECURE_DB_PASSWORD@localhost:5432/synapselm
SECRET_KEY=YOUR_GENERATED_JWT_SECRET
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

CREDENTIAL_ENCRYPTION_KEY=YOUR_GENERATED_FERNET_KEY
REDIS_URL=redis://localhost:6379/0
ALLOWED_ORIGINS=https://synapselm.example.com

LLM_PROVIDER=gemini
LLM_MODEL=gemini-3.6-flash
LLM_API_KEY=OPTIONAL_SYSTEM_FALLBACK_KEY
```

Set strict permissions:
```bash
chmod 600 /var/www/synapselm/backend/.env
```

### Step 3: Provision PostgreSQL and Run Migrations

```bash
# Create database user and database (in psql as postgres user)
sudo -u postgres psql << EOF
CREATE USER synapse_user WITH PASSWORD 'SECURE_DB_PASSWORD';
CREATE DATABASE synapselm OWNER synapse_user;
GRANT ALL PRIVILEGES ON DATABASE synapselm TO synapse_user;
EOF

# Run Alembic migrations to apply all schema revisions up to head
cd /var/www/synapselm/backend
source venv/bin/activate
alembic upgrade head

# Verify current revision
alembic current
```

Expected current revision: `590e4e31ede3 (head)`

### Step 4: Build the Frontend Production Assets

```bash
cd /var/www/synapselm/frontend
npm ci
npm run build
```
This produces optimized production assets in `/var/www/synapselm/frontend/dist/`.

### Step 5: Configure Systemd Service for Backend

Create `/etc/systemd/system/synapselm-backend.service`:

```ini
[Unit]
Description=SynapseLM FastAPI Backend
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/synapselm/backend
EnvironmentFile=/var/www/synapselm/backend/.env
ExecStart=/var/www/synapselm/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4 --proxy-headers --forwarded-allow-ips='*'
Restart=always
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo chown -R www-data:www-data /var/www/synapselm
sudo systemctl daemon-reload
sudo systemctl enable synapselm-backend
sudo systemctl start synapselm-backend
sudo systemctl status synapselm-backend
```

### Step 6: Configure NGINX Reverse Proxy with WebSocket Support

Create `/etc/nginx/sites-available/synapselm`:

```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}

server {
    server_name synapselm.example.com;

    # Frontend Static Files
    root /var/www/synapselm/frontend/dist;
    index index.html;

    # Client body limit for standard payload sizes
    client_max_body_size 10M;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # SPA Client Routing fallback
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Backend REST API
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health Check
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        proxy_set_header Host $host;
    }

    # WebSockets
    location /ws/ {
        proxy_pass http://127.0.0.1:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }
}
```

Enable the site and test configuration:
```bash
sudo ln -s /etc/nginx/sites-available/synapselm /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Step 7: Enable TLS/HTTPS via Let's Encrypt

```bash
sudo certbot --nginx -d synapselm.example.com
```
Certbot will obtain and configure the TLS certificates and set up automatic renewals.

---

## 5. Health Checks and Verification

Test that the services are responding properly:

```bash
# 1. Check HTTP Health endpoint
curl -s -i https://synapselm.example.com/health
# Expected: HTTP/2 200 OK, {"status":"ok","service":"SynapseLM API"}

# 2. Check Backend Service status
sudo systemctl status synapselm-backend --no-pager

# 3. Check Redis connectivity
redis-cli ping
# Expected: PONG

# 4. Check PostgreSQL connectivity
sudo -u postgres psql -d synapselm -c "SELECT count(*) FROM users;"
```

---

## 6. Database Backup and Disaster Recovery

### Automated Daily Backups
Create a daily backup script `/usr/local/bin/backup-synapselm.sh`:

```bash
#!/bin/bash
set -euo pipefail

BACKUP_DIR="/var/backups/synapselm"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/synapselm_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

# Dump database
pg_dump -U synapse_user -h localhost -d synapselm | gzip > "$BACKUP_FILE"
chmod 600 "$BACKUP_FILE"

# Keep last 14 days of backups
find "$BACKUP_DIR" -type f -name "synapselm_*.sql.gz" -mtime +14 -delete
```

Set up a cron job (`sudo crontab -e`):
```cron
0 2 * * * /usr/local/bin/backup-synapselm.sh
```

### Database Restoration Procedure
To restore from backup:

```bash
# 1. Stop backend service to prevent writes
sudo systemctl stop synapselm-backend

# 2. Re-create empty database
sudo -u postgres psql -c "DROP DATABASE synapselm;"
sudo -u postgres psql -c "CREATE DATABASE synapselm OWNER synapse_user;"

# 3. Restore data from compressed dump
gunzip -c /var/backups/synapselm/synapselm_YYYYMMDD_HHMMSS.sql.gz | psql -U synapse_user -h localhost -d synapselm

# 4. Verify Alembic migration state
cd /var/www/synapselm/backend
source venv/bin/activate
alembic current

# 5. Restart backend service
sudo systemctl start synapselm-backend
```

---

## 7. Updates and Rollback Procedure

### Safe Update Procedure

```bash
cd /var/www/synapselm

# 1. Fetch latest changes
git pull origin main

# 2. Upgrade Python dependencies
cd /var/www/synapselm/backend
source venv/bin/activate
pip install -r requirements.txt

# 3. Apply database migrations
alembic upgrade head

# 4. Build frontend
cd /var/www/synapselm/frontend
npm ci
npm run build

# 5. Restart backend service gracefully
sudo systemctl restart synapselm-backend

# 6. Verify health check
curl -f https://synapselm.example.com/health
```

### Rollback Procedure

If a deployment fails:

1. **Roll back Git code**:
   ```bash
   git checkout PREVIOUS_STABLE_COMMIT_HASH
   ```
2. **Roll back database migrations** (if applicable):
   ```bash
   cd /var/www/synapselm/backend
   source venv/bin/activate
   alembic downgrade TARGET_REVISION
   ```
   > [!NOTE]
   > All migrations in `backend/alembic/versions/` implement standard reversible `downgrade()` routines.
3. **Rebuild frontend**:
   ```bash
   cd /var/www/synapselm/frontend && npm ci && npm run build
   ```
4. **Restart backend**:
   ```bash
   sudo systemctl restart synapselm-backend
   ```

---

## 8. Deployment Handoff Checklist

### Pre-Deployment Checklist
- [ ] Server provisioned (Ubuntu 22.04 LTS or Debian 12 with public IP).
- [ ] Domain DNS configured (`synapselm.example.com` -> server IP).
- [ ] Python 3.10+, Node.js 20+, NGINX, Redis, PostgreSQL installed.
- [ ] `CREDENTIAL_ENCRYPTION_KEY` generated and recorded in a secure password vault.
- [ ] `SECRET_KEY` generated.
- [ ] `backend/.env` prepared with database credentials and secrets.
- [ ] Redis operational and accepting connections (`redis-cli ping` -> `PONG`).

### Deployment Checklist
- [ ] PostgreSQL user and database `synapselm` created.
- [ ] Alembic migrations executed: `alembic upgrade head` (reaches `590e4e31ede3`).
- [ ] Frontend build executed: `npm run build` succeeds with zero TypeScript errors.
- [ ] Systemd service `synapselm-backend.service` created, enabled, and started.
- [ ] NGINX configuration installed with WebSocket upgrade headers.
- [ ] Let's Encrypt TLS certificate installed via `certbot`.
- [ ] Health check verified: `curl https://synapselm.example.com/health` returns `200 OK`.

### Post-Deployment Verification (Smoke Tests)
- [ ] Navigate to `https://synapselm.example.com` in a browser.
- [ ] **Account A (Alice)**: Register a new account and log in.
- [ ] **Settings**: Go to `/settings`, add a personal API key (e.g. Gemini or OpenAI), and verify it saves.
- [ ] **Chat Creation**: Create a new conversation and send a message. Verify AI responds.
- [ ] **Share Flow**: Click the **Share** button in the header. Select expiration and click "Create Link". Verify copy link works.
- [ ] **Account B (Bob)**: Open an incognito window or second browser. Register Account B.
- [ ] **Share Preview**: Open the generated share link at `/shares/:token`. Verify preview shows Title and Alice's username.
- [ ] **Branching**: Click "Branch Conversation". Verify Bob is redirected to his isolated branch `/conversations/:branch_id` and sees previous snapshot history.
- [ ] **Collaboration Request**: Click "Request Access". Verify request is submitted.
- [ ] **Owner Approval**: As Alice, open the chat sidebar, observe "Pending Requests", and click "Accept". Verify Bob is added as a participant.
- [ ] **Security Check**: Check server logs (`journalctl -u synapselm-backend -n 100`) to confirm zero secret keys or tokens are leaked in plaintext.
