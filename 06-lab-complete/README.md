# Lab 12 — Complete Production Agent

Kết hợp TẤT CẢ những gì đã học trong 1 project hoàn chỉnh.

## Checklist Deliverable

- [x] Dockerfile (multi-stage, < 500 MB)
- [x] docker-compose.yml (agent + redis)
- [x] .dockerignore
- [x] Health check endpoint (`GET /health`)
- [x] Readiness endpoint (`GET /ready`)
- [x] API Key authentication
- [x] Rate limiting
- [x] Cost guard
- [x] Config từ environment variables
- [x] Structured logging
- [x] Graceful shutdown
- [x] Public URL ready (Railway / Render config)

---

## Cấu Trúc

```
06-lab-complete/
├── app/
│   ├── main.py         # Entry point — kết hợp tất cả
│   ├── config.py       # 12-factor config
│   ├── auth.py         # API Key + JWT
│   ├── rate_limiter.py # Rate limiting
│   └── cost_guard.py   # Budget protection
├── Dockerfile          # Multi-stage, production-ready
├── docker-compose.yml  # Full stack
├── railway.toml        # Deploy Railway
├── render.yaml         # Deploy Render
├── .env.example        # Template
├── .dockerignore
└── requirements.txt
```

---

## Chạy Local

```bash
# 1. Setup
cp .env.example .env

# 2. Chạy với Docker Compose
docker compose up

# 3. Test
curl http://localhost/health

# 4. Lấy API key từ .env, test endpoint
API_KEY=$(grep AGENT_API_KEY .env | cut -d= -f2)
curl -H "X-API-Key: $API_KEY" \
     -X POST http://localhost/ask \
     -H "Content-Type: application/json" \
     -d '{"question": "What is deployment?"}'
```

---

## Deploy Railway (< 5 phút)

```bash
# Cài Railway CLI
npm i -g @railway/cli

# Login và deploy
railway login
railway init
railway variables set OPENAI_API_KEY=sk-...
railway variables set AGENT_API_KEY=your-secret-key
railway up

# Nhận public URL!
railway domain
```

---

## Deploy Render

1. Push repo lên GitHub
2. Render Dashboard → New → Blueprint
3. Connect repo → Render đọc `render.yaml`
4. Set secrets: `OPENAI_API_KEY`, `AGENT_API_KEY`
5. Deploy → Nhận URL!

---

## Kiểm Tra Production Readiness

```bash
python check_production_ready.py
```

Script này kiểm tra tất cả items trong checklist và báo cáo những gì còn thiếu.

---

## CI/CD Pipeline (Bonus)

Workflow: [`.github/workflows/ci-cd.yml`](../.github/workflows/ci-cd.yml)

**CI job** (chạy trên mọi push/PR vào `main` khi có thay đổi trong `06-lab-complete/` hoặc `utils/`):
1. Cài dependencies (`requirements-dev.txt`)
2. Lint code với `ruff check app tests`
3. Chạy unit tests + coverage: `pytest --cov=app --cov-fail-under=70`
4. Upload coverage report (`coverage.xml`) làm artifact

**CD job** (chỉ chạy khi push vào `main` và CI pass):
- Deploy lên **Render** qua deploy hook (`RENDER_DEPLOY_HOOK_URL` secret), hoặc
- Deploy lên **Railway** qua Railway CLI (`RAILWAY_TOKEN` secret)

### Setup secrets

Trong GitHub repo → **Settings → Secrets and variables → Actions**, thêm 1 trong 2:

| Secret | Platform | Cách lấy |
|---|---|---|
| `RENDER_DEPLOY_HOOK_URL` | Render | Dashboard service → Settings → Deploy Hook |
| `RAILWAY_TOKEN` | Railway | `railway login` → Account Settings → Tokens |

Nếu không có secret nào, job `deploy` chạy nhưng sẽ chỉ in warning và skip.

### Run tests locally

```bash
pip install -r requirements-dev.txt
ruff check app tests
PYTHONPATH=..:. pytest tests -v --cov=app --cov-report=term-missing
```
