# Deployment

## Architecture

The production stack is defined in `docker-compose.prod.yml`:

- **Caddy** terminates HTTPS and routes `/api/*` to the API and everything else to the web app.
- **Frontend**: Next.js 15 in `frontend/`, built with `NEXT_PUBLIC_API_URL` baked in.
- **Backend**: FastAPI in `backend/`, started via `backend/start.sh` which runs `alembic upgrade head` before Uvicorn.
- **Data**: PostgreSQL 16 with `pgvector`, plus Redis.
- **Workers**: Celery worker and Celery Beat for scheduled digests.

## Local Docker + Cloudflare Quick Tunnel (no VPS)

Use this when you want a public HTTPS URL without renting a VPS or configuring DNS:

```bash
# 1. Start the full stack. Caddy publishes only host port 8080 in this mode.
docker compose -f docker-compose.tunnel.yml up -d --build --wait

# 2. Download cloudflared (Windows example), then start a free quick tunnel.
cloudflared tunnel --no-autoupdate --url http://localhost:8080
```

`cloudflared` prints a public URL such as
`https://example-trycloudflare-subdomain.trycloudflare.com`. Open `/radar` and
verify `/api/health` on that origin. The frontend uses a relative API base
(`/api/v1`), so no rebuild is needed when the random hostname changes.

Notes:

- This machine must stay powered on with Docker and `cloudflared` running.
- A Quick Tunnel URL is random and changes whenever `cloudflared` restarts.
- For a stable custom hostname, use a named Cloudflare Tunnel with a domain
  whose DNS is managed by Cloudflare, then switch back to
  `docker-compose.prod.yml`.

## Docker deployment (primary)

### 1. Prepare the VPS

Use a Linux VPS with Docker Engine and the Compose plugin installed. Open ports
`80` and `443`, and point your domain’s DNS A record at the VPS IP.

```bash
git clone https://github.com/PRANAV-DEV-20/student-radar.git
cd student-radar
cp .env.example .env
```

`0.0.0.0` is only a bind address meaning “listen on all interfaces”. It is not
an address you can SSH to. Use the VPS public IP or DNS name, e.g.
`root@203.0.113.10`.

### 2. SSH access (remote deploy)

Generate a key on the machine that will run the deployment:

```bash
ssh-keygen -t ed25519 -C "student-radar-deploy" -f ~/.ssh/id_ed25519_student_radar
```

Copy only the **public** key (`~/.ssh/id_ed25519_student_radar.pub`) to the VPS:

```bash
ssh-copy-id -i ~/.ssh/id_ed25519_student_radar.pub root@<VPS_IP>
```

Or add it manually on the VPS:

```bash
mkdir -p /root/.ssh
echo 'ssh-ed25519 AAAA... student-radar-deploy' >> /root/.ssh/authorized_keys
chmod 700 /root/.ssh
chmod 600 /root/.ssh/authorized_keys
```

Never share the private key (`id_ed25519_student_radar`). Test with:

```bash
ssh -i ~/.ssh/id_ed25519_student_radar root@<VPS_IP>
```

### 3. Configure `.env`

At minimum, set:

```env
DOMAIN=radar.example.com
CORS_ORIGINS=https://radar.example.com
NEXT_PUBLIC_API_URL=https://radar.example.com/api/v1
NEXT_PUBLIC_APP_URL=https://radar.example.com
POSTGRES_PASSWORD=<long-random-value>
JWT_SECRET=<long-random-value>
GEMINI_API_KEY=<your-key>
TAVILY_API_KEY=<your-key>
EXA_API_KEY=<optional>
ENABLE_CELERY_DISPATCH=true
```

`NEXT_PUBLIC_API_URL` is baked into the frontend at build time, so set it before
building the image.

### 4. Start the stack

```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml logs -f
```

The site will be available at `https://$DOMAIN`. The API health check is
`GET /health` behind `/api/health`.

### 5. Useful commands

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml restart backend
docker compose -f docker-compose.prod.yml down
```

To deploy a new version:

```bash
git pull origin main
docker compose -f docker-compose.prod.yml up -d --build
```

## Free domain with DuckDNS

1. Sign in at https://www.duckdns.org and create a domain such as
   `student-radar-xyz.duckdns.org`.
2. Set its **current IP** to your VPS public IP.
3. Use that domain in `.env`:

   ```env
   DOMAIN=student-radar-xyz.duckdns.org
   CORS_ORIGINS=https://student-radar-xyz.duckdns.org
   NEXT_PUBLIC_API_URL=https://student-radar-xyz.duckdns.org/api/v1
   NEXT_PUBLIC_APP_URL=https://student-radar-xyz.duckdns.org
   ```

4. Make sure VPS ports `80` and `443` are open, then start the stack. Caddy will
   request and renew a Let’s Encrypt certificate automatically.

If your VPS IP changes, update the DuckDNS record (or run their update cron).
A static IP avoids this step.

## Local development

```bash
cp .env.example .env
docker compose up --build
```

The frontend runs at `http://localhost:3000` and the API at
`http://localhost:8000`.

If another application already owns those ports, use the alternate-port setup.
It publishes the frontend on `http://localhost:3200`, Postgres on `55433` and
Redis on `6380` with isolated container/volume names, and bakes
`http://localhost:8100/api/v1` into the frontend at build time.

```bash
docker compose -f docker-compose.alt.yml up -d --build
```

Run the API from host Python on port 8100 (no backend image build required):

```powershell
cd backend
$env:DATABASE_URL="postgresql+asyncpg://radar_admin:radar_secret_pass@localhost:55433/student_radar_db"
$env:SYNC_DATABASE_URL="postgresql+psycopg2://radar_admin:radar_secret_pass@localhost:55433/student_radar_db"
$env:REDIS_URL="redis://localhost:6380/0"
$env:CORS_ORIGINS="http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001,http://localhost:3002,http://127.0.0.1:3002,http://localhost:3003,http://127.0.0.1:3003,http://localhost:3200,http://127.0.0.1:3200"
$env:PORT="8100"
python -m alembic upgrade head
python -m uvicorn app.main:app --host 0.0.0.0 --port 8100
```

If the API must survive after the PowerShell window closes, start it detached:

```powershell
$env:DATABASE_URL="postgresql+asyncpg://radar_admin:radar_secret_pass@localhost:55433/student_radar_db"
$env:SYNC_DATABASE_URL="postgresql://radar_admin:radar_secret_pass@localhost:55433/student_radar_db"
$env:REDIS_URL="redis://localhost:6380/0"
$env:CORS_ORIGINS="http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001,http://localhost:3002,http://127.0.0.1:3002,http://localhost:3003,http://127.0.0.1:3003,http://localhost:3200,http://127.0.0.1:3200"
Start-Process python -ArgumentList "-m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8100" -WindowStyle Hidden
```

Set `GEMINI_API_KEY` / `TAVILY_API_KEY` in the same shell if you want live AI
and search results; without them the API still serves the grounded DB records.

For a local dev server (`npm run dev` in `frontend/`), `frontend/.env.local`
points `NEXT_PUBLIC_API_URL` at the same `8100` API, and the CORS list above
includes dev ports `3000`–`3003` as well as the Docker frontend on `3200`.

Never run `next build` and `next dev` in this folder at the same time: both use
`.next`, and the build deletes/replaces the dev server's manifests, causing
`Cannot find module ... middleware-manifest.json` or stale
`/_next/static/... 404` errors. The local dev server is therefore started with
an isolated output directory:

```powershell
cd frontend
$env:PORT = "3001"
$env:NEXT_DIST_DIR = ".next-dev"
npm run dev
```

`next.config.ts` reads `NEXT_DIST_DIR` and otherwise defaults to `.next`, so
production builds are unchanged. If you already saw a stale-chunk error, hard
refresh the browser (`Ctrl+Shift+R`).

To stop the alternate stack later:

```powershell
docker compose -f docker-compose.alt.yml down
```

Then press `Ctrl+C` in the terminal running `uvicorn` to stop the API. If it
was started detached, stop it with:

```powershell
Get-NetTCPConnection -LocalPort 8100 -State Listen |
  ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

### Troubleshooting: `TypeError: Failed to fetch`

This is a browser network error from the frontend calling `NEXT_PUBLIC_API_URL`.
It is not an application logic bug. Check, in order:

1. The API is actually running for **this** project:
   `curl http://localhost:8000/api/v1/radar/briefing?persona=tech_builder`
   should return JSON (a 404 means a different service owns port 8000 — stop it
   or run this stack on another port).
2. `NEXT_PUBLIC_API_URL` is correct for where the frontend is served. It is
   **baked in at build time**, so rebuild the frontend after changing it. Use a
   reachable absolute URL (or `/api/v1` when a reverse proxy serves the API on
   the same origin). Never ship `http://localhost:8000` in a deployed build.
3. The browser origin is listed in the backend's `CORS_ORIGINS` (a CORS
   rejection also surfaces as `Failed to fetch`).
4. An HTTPS page must call an HTTPS API — mixing HTTPS → HTTP is blocked.

The Radar keeps the last successful briefing and shows an "unavailable" notice
instead of replacing it with invented records; there is deliberately no local
fallback for Radar data.

For Dossier v2 runs, an `All models failed ... HTTP 429/503` error means the AI
provider is rate-limited or temporarily unavailable, not that the input was too
long. Wait a minute and rerun the generation.

## Vercel + Render (alternative)

`render.yaml` and `frontend/vercel.json` are kept as an alternative managed
deployment path. Render creates Postgres, Redis, and the FastAPI web service;
Vercel builds the Next.js frontend with `NEXT_PUBLIC_API_URL` pointing at the
Render service.

Safe deployment order:

1. Deploy the Render backend first and confirm `GET /health` returns `200`.
2. In Vercel, import the repository with **Root Directory = `frontend`** and
   framework **Next.js**.
3. Set only public frontend variables in Vercel:

   ```text
   NEXT_PUBLIC_API_URL=https://<render-service>.onrender.com/api/v1
   NEXT_PUBLIC_APP_URL=https://<your-vercel-domain>
   ```

   Never put `GEMINI_API_KEY`, `GROQ_API_KEY`, `TAVILY_API_KEY`,
   `DATABASE_URL`, or `JWT_SECRET` in Vercel. Anything named `NEXT_PUBLIC_*`
   is visible in the browser bundle.
4. Set the backend secrets in Render: `GEMINI_API_KEY`, `GROQ_API_KEY`,
   `TAVILY_API_KEY`, `EXA_API_KEY`, and a generated `JWT_SECRET`.
5. Set `CORS_ORIGINS` on Render to the exact Vercel origin(s), for example
   `https://your-app.vercel.app`. Add preview deployment origins only when you
   trust them; do not allow wildcard `https://*.vercel.app` with credentials.
6. Deploy Vercel **after** the backend URL is final, because
   `NEXT_PUBLIC_API_URL` is baked into the bundle at build time. Use HTTPS for
   both sides to avoid mixed-content `Failed to fetch` errors.
