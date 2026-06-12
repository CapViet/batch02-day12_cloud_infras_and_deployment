# Lab 12 — Multi-Agent Legal Assistant (Productionized)

Productionized version of the Day 09 multi-agent system (`law_agent` +
`tax_agent` + `compliance_agent`) — re-implemented as a single stateless
FastAPI service applying every Day 12 productionization step.

`POST /ask` runs the Law agent, and — based on keyword routing — the Tax
and/or Compliance specialist agents **in parallel** (`asyncio.gather`), then
synthesises a combined answer. See `app/agents/orchestrator.py`.

Without `GOOGLE_API_KEY` set, all agents run in **mock mode** (deterministic
canned responses) so the service is fully testable/demo-able with no LLM key.

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
│   ├── main.py         # Entry point — auth, rate limit, cost guard, health/ready
│   ├── config.py       # 12-factor config (env vars)
│   ├── static/
│   │   └── index.html  # Chat UI (served at GET /)
│   └── agents/
│       ├── orchestrator.py   # Multi-agent routing + parallel dispatch
│       ├── prompts.py        # Law / Tax / Compliance system prompts
│       ├── llm_client.py     # Gemini client (OpenAI-compatible)
│       └── mock_responses.py # Mock-mode fallback answers
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
     -d '{"question": "What are the tax evasion penalties for offshore accounts?"}'
```

---

## Deploy Railway (< 5 phút)

```bash
# Cài Railway CLI
npm i -g @railway/cli

# Login và deploy
railway login
railway init
railway variables set GOOGLE_API_KEY=your-gemini-key   # optional — omit for mock mode
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
