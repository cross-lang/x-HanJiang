# HanJiang Deployment Guide — Alibaba Cloud Lightweight Application Server

> Cost-effective single-machine demo deployment: one 2C4G Lightweight Application Server, Docker Compose brings up all services with one command, accessed directly by IP (no domain / HTTPS).

## Architecture

```
Browser ── http://<SERVER_IP>
              │
        ┌─────▼─────┐
        │  nginx:80  │  Frontend hosting + unified entry
        │            │  /           → Admin console SPA
        │            │  /portal/    → Open platform portal SPA
        └─────┬──────┘  /api/        → Reverse proxy to backend (injects X-Real-IP)
              │
        ┌─────▼─────┐   ┌─────────┐   ┌─────────┐
        │  app:8000  │──▶│ mysql:8 │   │ redis:7 │
        │  FastAPI   │   └─────────┘   └─────────┘
        └────────────┘   (all orchestrated by docker-compose on the same host)
```

- Frontend builds run inside `web/Dockerfile` (Node multi-stage build) — no Node.js needed on the server
- Database initialization happens automatically at app startup (`init_db` creates tables + `init_seed_data` seeds data) — no manual migration
- MySQL / Redis run as self-hosted containers, persisted in the `mysql_data` / `redis_data` volumes

## 1. Prerequisites

| Item | Requirement |
|---|---|
| Server | Alibaba Cloud **Lightweight Application Server**, 2 vCPU / 4 GiB (2 GiB will OOM — compose resource limits sum to ~2.5G) |
| Image | Alibaba Cloud Linux 3 or Ubuntu 24.04 |
| Firewall / security group | Allow **80** (HTTP) and **22** (SSH); 8000/3306/6379 stay internal |
| Local | Code pushed to a Git repository (Gitee / GitHub both fine) |

## 2. Initialize the Server (Install Docker)

SSH into the server:

```bash
# Install Docker (official script; works on Alibaba Cloud Linux / Ubuntu)
curl -fsSL https://get.docker.com | bash
sudo systemctl enable --now docker

# Verify (Compose V2 ships as a docker plugin)
sudo docker compose version

# (Optional) run docker without sudo
sudo usermod -aG docker $USER && newgrp docker
```

> If pulling images is slow in China, configure a registry mirror in `/etc/docker/daemon.json` (Alibaba Cloud Container Registry console provides a dedicated accelerator).

**Extra step for 2 GiB plans: add a 2G swap file (prevents occasional OOM)**

```bash
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile \
  && sudo mkswap /swapfile && sudo swapon /swapfile \
  && echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## 3. Get the Code

```bash
sudo mkdir -p /opt/x-HanJiang && cd /opt/x-HanJiang
git clone <your-repo-url> .
```

> Alternatively, pack locally and upload: `git archive -o /tmp/hanjiang.tar HEAD`, then `scp /tmp/hanjiang.tar user@<SERVER_IP>:/opt/x-HanJiang/` and extract.

## 4. Prepare Environment Variables

Create a `.env` file in the **project root** (next to `docker-compose.yml`):

```bash
cd /opt/x-HanJiang
cat > .env <<'EOF'
APP_ENV=production

# JWT secret: must be ≥32 random chars (generate with the command below)
AUTH_SECRET_KEY=<output of: openssl rand -hex 32>

# Database (when MYSQL_USER defaults to root, MYSQL_PASSWORD must equal MYSQL_ROOT_PASSWORD)
MYSQL_ROOT_PASSWORD=<strong-password-1>
MYSQL_PASSWORD=<strong-password-1>
MYSQL_DATABASE=hanjiang

# Redis
REDIS_PASSWORD=<strong-password-2>

# LLM API key for the AI assistant (Xiaomi MiMo / DeepSeek / any OpenAI-compatible provider)
AI_LLM_API_KEY=<your-key>
EOF

# Generate a random secret:
openssl rand -hex 32
```

> Gunicorn defaults to 4 workers; if memory is tight, append `GUNICORN_WORKERS=2` to `.env`.

## 5. Build and Start

```bash
cd /opt/x-HanJiang
docker compose up -d --build
```

First build takes ~5–15 minutes (frontend `npm ci` and backend `uv sync` are cached in Docker layers; subsequent builds are fast).

## 6. Verify

| Check | URL | Expected |
|---|---|---|
| Container health | `docker compose ps` | app / nginx / mysql / redis all running (healthy) |
| Admin console | `http://<SERVER_IP>/` | Login page renders |
| Open platform portal | `http://<SERVER_IP>/portal/` | Portal home renders |
| API docs | `http://<SERVER_IP>/docs` | Swagger UI opens |
| Health check | `http://<SERVER_IP>/api/admin/v1/health` | Returns healthy status |

Initial admin account (auto-created by seed data): `superadmin` / `admin@123456`
**Change the password immediately after first login** (Profile → Change Password).

## 7. Daily Operations

```bash
# Logs
docker compose logs -f app        # backend
docker compose logs -f nginx      # frontend & entry traffic

# Redeploy after code changes
git pull
docker compose up -d --build

# Restart / stop
docker compose restart app
docker compose down               # keeps data volumes
docker compose down -v            # DANGEROUS: also deletes database data

# Backup (periodic is fine for demo)
docker compose exec mysql sh -c 'mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" hanjiang' > backup_$(date +%F).sql
```

## 8. Troubleshooting

| Symptom | Cause & Fix |
|---|---|
| app container keeps restarting | Out of memory: append `GUNICORN_WORKERS=2` to `.env`, then `docker compose up -d` |
| 502 on pages | app not yet healthy or crashed: check `docker compose logs app`; nginx waits on `service_healthy` automatically |
| AI assistant errors / no reply | `AI_LLM_API_KEY` missing or invalid in `.env`; the key is injected via environment variables — recreate app with `docker compose up -d` after changes |
| npm/uv timeout during build | Network issue: configure a Docker registry mirror, or retry (layer cache skips completed steps) |
| Where are log files | Inside the app container at `/app/logs/` (hourly rotation); list via `docker compose exec app ls logs` |
| Security reminder | After the demo, run `docker compose down` to release costs; remove the `/docs` location block in `web/nginx.conf` if not needed |
