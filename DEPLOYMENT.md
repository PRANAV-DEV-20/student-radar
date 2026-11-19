# Deployment

## Architecture

The production stack is defined in `docker-compose.prod.yml`:

- **Caddy** terminates HTTPS and routes `/api/*` to the API and everything else to the web app.
- **Frontend**: Next.js 15 in `frontend/`, built with `NEXT_PUBLIC_API_URL` baked in.
- **Backend**: FastAPI in `backend/`, started via `backend/start.sh` which runs `alembic upgrade head` before Uvicorn.
- **Data**: PostgreSQL 16 with `pgvector`, plus Redis.
- **Workers**: Celery worker and Celery Beat for scheduled digests.

## Docker deployment (primary)

### 1. Prepare the VPS

Use a Linux VPS with Docker Engine and the Compose plugin installed. Open ports
`80` and `443`, and point your domain’s DNS A record at the VPS IP.

```bash
git clone https://github.com/PRANAV-DEV-20/student-radar.git
cd student-radar
cp .env.example .env
```

### 2. Configure `.env`

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

### 3. Start the stack

```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml logs -f
```

The site will be available at `https://$DOMAIN`. The API health check is
`GET /health` behind `/api/health`.

### 4. Useful commands

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

## Vercel + Render (alternative)

`render.yaml` and `frontend/vercel.json` are kept as an alternative managed
deployment path. Render creates Postgres, Redis, and the FastAPI web service;
Vercel builds the Next.js frontend with `NEXT_PUBLIC_API_URL` pointing at the
Render service. For that path, set `CORS_ORIGINS` to the Vercel domain.
