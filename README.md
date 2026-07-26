# PulseWatch
# URL Health Audit & Monitoring Service

## Project Structure

```
url_audit/
├── backend/          # Django + DRF API
├── frontend/         # React SPA (Vite)
├── nginx/            # Reverse proxy config
├── docs/             # Project documentation (6 docs)
└── docker-compose.yml
```

## Quick Start

```bash
# Copy environment file
cp .env.example .env
# Edit .env with your values

# Start all services
docker-compose up --build

# Run migrations
docker-compose exec web python manage.py migrate

# Access the app
# Frontend: http://localhost
# API: http://localhost/api/
# Swagger docs: http://localhost/api/docs/
# Health check: http://localhost/api/health/
```

## API Contract

### Check/Audit (Must-have)

#### `POST /api/audits` — Run an on-demand URL check
```json
// Request
{ "url": "https://example.com" }

// Response — 200 OK
{
  "success": true,
  "request_id": "req_9f3a2b1c",
  "data": {
    "audit_id": "aud_7c1e4d90",
    "url": "https://example.com/",
    "cache": "miss",
    "checked_at": "2026-07-25T10:15:00Z",
    "result": {
      "availability": { "reachable": true, "status_code": 200, "redirect_count": 0 },
      "performance": { "response_time_ms": 214, "ttfb_ms": 120, "page_size_bytes": 48213 },
      "seo_signals": { "title_present": true, "title_length": 42, "meta_description_present": true, "h1_count": 1 },
      "security_headers": { "hsts": true, "csp": false, "x_frame_options": true, "x_content_type_options": true }
    }
  },
  "timestamp": "2026-07-25T10:15:00Z"
}
```

#### `GET /api/audits/{audit_id}` — Fetch a completed audit
Same response shape. `404 AUDIT_NOT_FOUND` if unknown/expired.

### Monitor (Should-have)

#### `POST /api/monitors` — Register recurring checks
```json
// Request
{
  "url": "https://example.com",
  "interval_seconds": 300,
  "webhook_url": "https://client.example/webhooks/pulsewatch",
  "latency_threshold_ms": 2000
}

// Response — 201 Created
{
  "success": true,
  "request_id": "req_1a2b3c4d",
  "data": {
    "monitor_id": "mon_5e6f7a8b",
    "url": "https://example.com/",
    "interval_seconds": 300,
    "state": "PENDING_FIRST_CHECK",
    "next_check_at": "2026-07-25T10:20:00Z"
  },
  "timestamp": "2026-07-25T10:15:00Z"
}
```

#### `GET /api/monitors` — List your monitors
Scoped by `X-Client-Key` header.

#### `GET /api/monitors/{monitor_id}` — Monitor status
#### `GET /api/monitors/{monitor_id}/history?limit=50` — Check history
#### `DELETE /api/monitors/{monitor_id}` — Stop monitoring

### Error Responses
All errors follow the shape:
```json
{ "success": false, "request_id": "req_...", "error": { "code": "...", "message": "..." }, "timestamp": "..." }
```

| HTTP | Code | When |
|---|---|---|
| 400 | `INVALID_URL` | Malformed URL, unsupported scheme |
| 400 | `URL_NOT_ALLOWED` | Resolves to private/internal IP |
| 400 | `INTERVAL_TOO_SHORT` | Monitor interval below minimum |
| 404 | `AUDIT_NOT_FOUND` / `MONITOR_NOT_FOUND` | Unknown ID |
| 429 | `RATE_LIMITED` | Too many requests (includes Retry-After) |
| 502 | `TARGET_UNREACHABLE` | DNS failure, connection refused |
| 504 | `TARGET_TIMEOUT` | Fetch exceeded timeout |
| 503 | `SERVICE_BUSY` | Concurrency limit reached |
| 500 | `INTERNAL_ERROR` | Unhandled error |

## ⚠️ Subpath Deployment Notice

This project is configured to be served at **`/url-audit-project`** (not root `/`). If you clone this repo and want to deploy it at a **different path or at root**, you must update the following files:

| # | File | What to change | Current value |
|---|---|---|---|
| 1 | `frontend/vite.config.js` | `base` option | `'/url-audit-project/'` |
| 2 | `frontend/src/App.jsx` | `<BrowserRouter basename="...">` | `"/url-audit-project"` |
| 3 | `frontend/src/api/client.js` | `API_BASE` constant | `'/url-audit-project'` |
| 4 | `backend/pulsewatch/settings.py` | `STATIC_URL` | `"/url-audit-project/static/"` |
| 5 | `backend/pulsewatch/settings.py` | `FORCE_SCRIPT_NAME` | `"/url-audit-project"` |
| 6 | `nginx/nginx.conf` | All `location` paths | prefixed with `/url-audit-project` |
| 7 | `docker-compose.prod.yml` | `ports` for nginx | `"127.0.0.1:8080:80"` |

### To deploy at root `/` instead

1. **`vite.config.js`** — remove the `base` line (or set to `'/'`)
2. **`App.jsx`** — change to `<BrowserRouter>` (remove `basename`)
3. **`client.js`** — change `API_BASE` to `''`
4. **`settings.py`** — change `STATIC_URL` to `"/static/"` and remove `FORCE_SCRIPT_NAME`
5. **`nginx.conf`** — remove `/url-audit-project` from all `location` blocks and `rewrite` rules
6. **`docker-compose.prod.yml`** — change port to `"80:80"` (or keep `8080` if behind a reverse proxy)

After changes, rebuild the frontend:

```bash
cd frontend
npm run build
```

## Live Deployment

**URL:** [https://itsaliya.in/url-audit-project](https://itsaliya.in/url-audit-project)

---

Built for [Digital Heroes Training Task](https://digitalheroesco.com)
