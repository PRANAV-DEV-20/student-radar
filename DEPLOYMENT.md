# Deployment

## Architecture

- **Frontend**: Next.js app in `frontend/`, deployed to Vercel.
- **Backend**: FastAPI app in `backend/`, deployed as a Docker Web Service on Render.
- **Data**: Render PostgreSQL 16 with `pgvector` and Render Redis.
- **Migrations**: `backend/start.sh` normalizes the database URL and runs
  `alembic upgrade head` before starting Uvicorn.

## GitHub

The repo has no configured remote yet. Create an empty GitHub repository named
`student-radar`, then add the remote and push:

```bash
git remote add origin https://github.com/<owner>/student-radar.git
git add -A
git commit -m "feat: source-backed radar and production deployment setup"
git push -u origin main
```

## Render

1. Create a new **Blueprint** from `render.yaml`.
2. Fill the `sync: false` environment variables:
   - `GEMINI_API_KEY`
   - `TAVILY_API_KEY`
   - `EXA_API_KEY` (optional fallback)
3. `JWT_SECRET` is generated automatically by Render.
4. After Vercel deploys, set `CORS_ORIGINS` to the real Vercel domain, e.g.
   `https://student-radar.vercel.app`.
5. The API health check is `GET /health`.

## Vercel

1. Import the GitHub repo.
2. Set **Root Directory** to `frontend`.
3. Framework preset: **Next.js**.
4. Add environment variable:
   - `NEXT_PUBLIC_API_URL=https://<render-service>.onrender.com/api/v1`
5. Deploy.

## Local Docker preview

```bash
docker compose up --build
```

The frontend runs at `http://localhost:3000` and the API at
`http://localhost:8000`.
