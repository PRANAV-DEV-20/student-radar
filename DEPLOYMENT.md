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

## Vercel + Render (alternative)

`render.yaml` and `frontend/vercel.json` are kept as an alternative managed
deployment path. Render creates Postgres, Redis, and the FastAPI web service;
Vercel builds the Next.js frontend with `NEXT_PUBLIC_API_URL` pointing at the
Render service. For that path, set `CORS_ORIGINS` to the Vercel domain.
