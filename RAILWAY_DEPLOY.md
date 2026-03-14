# Railway Deployment Guide — PodClip.AI Backend

## Architecture on Railway

```
Railway Project
├── Backend Service      (FastAPI — port auto-assigned by Railway)
├── PostgreSQL Service   (managed by Railway)
├── Redis Service        (managed by Railway — optional)
├── ML Service           (FastAPI — optional, can be disabled initially)
```

---

## Step 1: Backend Service Environment Variables

In Railway → Backend service → Variables tab, set **exactly** these:

```
DATABASE_URL=${{Postgres.DATABASE_URL}}
SECRET_KEY=<run: openssl rand -hex 32>
ACCESS_TOKEN_EXPIRE_MINUTES=11520
PODCHASER_API_KEY=a0f78419-c723-4b03-a264-438b5d95cdde
PODCHASER_API_SECRET=JKZfJJ77lVNpb60GhbUybeKwl0O1ztyGYSIMvs2Z
PROJECT_NAME=podclip-backend
```

**Optional (add when services are deployed):**
```
REDIS_URL=${{Redis.REDIS_URL}}
ML_SERVICE_URL=https://<your-ml-service>.up.railway.app
```

**Optional (add when Razorpay is configured):**
```
RAZORPAY_KEY_ID=<your_key>
RAZORPAY_KEY_SECRET=<your_secret>
RAZORPAY_WEBHOOK_SECRET=<your_webhook_secret>
```

> ⚠️ **IMPORTANT**: `${{Postgres.DATABASE_URL}}` is a Railway reference variable.
> Replace `Postgres` with the exact name of your PostgreSQL service in Railway.
> If your service is named "PostgreSQL", use `${{PostgreSQL.DATABASE_URL}}`.

---

## Step 2: PostgreSQL Service

Railway auto-provisions PostgreSQL. No extra config needed.

The backend connects using `DATABASE_URL` which Railway injects automatically
when you use the `${{Postgres.DATABASE_URL}}` reference.

**Tables are auto-created on first startup** via SQLAlchemy's `create_all()`.

---

## Step 3: Redis Service (Optional)

Redis is used for:
- Match quota limits (free tier: 10 outreaches/30 days)
- Real-time chat pub/sub (multi-instance WebSocket delivery)
- Caching

**Without Redis**, the app still works — quota limits are disabled and chat
works in single-instance local-delivery mode.

To add Redis:
1. Railway → New Service → Redis
2. Copy the `REDIS_URL` from Redis service → Connect tab
3. Add to Backend service variables: `REDIS_URL=${{Redis.REDIS_URL}}`

---

## Step 4: Build Configuration

The backend uses a **Dockerfile** build. In Railway:
- Settings → Build → Builder: **Dockerfile**
- Dockerfile Path: `infra/docker/backend.Dockerfile`
- Build Context: `/` (repo root, so Docker can access `apps/backend/`)

Railway automatically sets `$PORT` — the Dockerfile CMD uses `${PORT:-8000}`.

---

---

## Step 5: Health Check

The backend exposes `/health` which Railway uses for health checks.
Set in Railway → Backend service → Settings → Health Check Path: `/health`

---

## Troubleshooting

### "Connection refused" to PostgreSQL
- Verify `DATABASE_URL` uses Railway's internal hostname (`postgres.railway.internal`)
  for services in the same Railway project, or the public URL for external access.
- The backend adds `sslmode=require` automatically when the URL contains "railway".

### "REDIS_URL not set" warning in logs
- This is expected if you haven't added Redis yet. The app runs fine without it.

### "ML service unavailable" in logs
- Expected if ML service isn't deployed. The recommendation feed falls back to
  returning users from the database sorted by creation date.

### App crashes on startup
- Check that `DATABASE_URL` is set and the PostgreSQL service is running.
- Check Railway logs: `railway logs --service backend`

### Tables not created
- The backend calls `Base.metadata.create_all()` on startup automatically.
- If it fails, check the DATABASE_URL is correct and the DB is reachable.

---

## Variables to REMOVE from Railway (if present)

These are leftover from earlier configs and will cause confusion:
- `NEXT_PUBLIC_API_URL` (belongs in Frontend service only)
- `NEXT_PUBLIC_ML_URL` (belongs in Frontend service only)
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` (not needed; use `DATABASE_URL`)
- `REDIS_PASSWORD` (not needed; use full `REDIS_URL`)

---

## Generating a Secure SECRET_KEY

```bash
openssl rand -hex 32
```

Copy the output and set it as `SECRET_KEY` in Railway.
