# Deployment — Multi-Agent Legal Assistant

## Live URL

**`https://day12-agent-production-b2bd.up.railway.app`**

Open it in a browser for the chat UI (enter the `AGENT_API_KEY` value once —
saved in `localStorage` — then ask a legal question). Raw API info at
`/api/info`.

- Platform: **Railway**
- Project: `day12-agent` (Project ID `734c382a-3bfc-46a8-a7cb-717ce3ebd4e2`)
- Service: `day12-agent`, Environment: `production`
- Build: Docker (`06-lab-complete/Dockerfile`, multi-stage, `python:3.11-slim`)
- Config: [`railway.json`](../railway.json) → `06-lab-complete/Dockerfile`,
  start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2`,
  healthcheck `/health`

## What this is

Productionized re-implementation of the **Day 09 multi-agent legal system**
(`law_agent` + `tax_agent` + `compliance_agent` from
`Batch02-Day9_Multi-Agent_MCP-A2A`). The original used an A2A
(agent-to-agent) protocol with a registry and 4 separate HTTP services
(customer/law/tax/compliance agents + registry). For this lab, it was
restructured into a **single stateless FastAPI service**:

- `app/agents/orchestrator.py` — routes the question to the **Law** agent,
  and — based on keyword detection (tax/compliance terms) — dispatches the
  **Tax** and/or **Compliance** specialist agents **concurrently**
  (`asyncio.gather`, replacing the A2A `Send`/registry delegation), then
  synthesises a final answer.
- `app/agents/llm_client.py` — Gemini via Google's OpenAI-compatible
  endpoint (`GOOGLE_API_KEY` / `GOOGLE_MODEL`).
- `app/agents/mock_responses.py` / `mock_responses` fallback — if
  `GOOGLE_API_KEY` is not set, every agent returns a deterministic mock
  answer so the service is fully testable/demo-able with zero LLM cost.

## Productionization steps applied (Day 12 checklist)

| Step | Implementation |
|---|---|
| 12-factor config | `app/config.py` — all settings via env vars (dataclass `Settings`) |
| Docker multi-stage build | `Dockerfile` — builder (`gcc`, `pip install --user`) + slim runtime, non-root `agent` user |
| API Key auth | `X-API-Key` header, `verify_api_key` dependency (`AGENT_API_KEY`) |
| JWT support | `JWT_SECRET` configured (HS256), reusable by `/auth/token`-style flows |
| Rate limiting | Sliding-window counter, `RATE_LIMIT_PER_MINUTE=20`, `429 Retry-After: 60` |
| Cost guard | Daily token-cost budget, `DAILY_BUDGET_USD=5.0`, `503` when exhausted |
| Health check | `GET /health` — liveness probe |
| Readiness check | `GET /ready` — readiness probe (503 until lifespan startup completes) |
| Graceful shutdown | `SIGTERM` handler + `timeout_graceful_shutdown=30` |
| Stateless design | No per-request state kept in memory; orchestration is pure async functions (Redis-ready via `REDIS_URL` if session state is added) |
| Structured JSON logging | `logging` with JSON format for every request/event |
| CI/CD | [`.github/workflows/ci-cd.yml`](../.github/workflows/ci-cd.yml) — ruff lint + pytest/coverage (CI), Railway/Render deploy (CD) |

## Environment variables (Railway)

| Variable | Value | Notes |
|---|---|---|
| `AGENT_API_KEY` | `my-secret-key-day12` | Required for `/ask`, `/metrics` |
| `JWT_SECRET` | *(generated, 32-byte urlsafe)* | For JWT-based flows |
| `ENVIRONMENT` | `production` | Enforces non-default secrets, disables `/docs` |
| `RATE_LIMIT_PER_MINUTE` | `20` | Sliding window per API key |
| `DAILY_BUDGET_USD` | `5.0` | Daily cost guard |
| `GOOGLE_API_KEY` | *(not set)* | Optional — leave empty to run in **mock mode** (current state). Set a Gemini key to enable real LLM responses. |
| `GOOGLE_MODEL` | `gemini-2.0-flash` (default) | Only used if `GOOGLE_API_KEY` is set |

## Verified endpoints (live test results)

```bash
$ curl -o /dev/null -w "%{http_code} %{content_type}\n" https://day12-agent-production-b2bd.up.railway.app/
200 text/html; charset=utf-8   # chat UI (app/static/index.html)

$ curl https://day12-agent-production-b2bd.up.railway.app/api/info
{"app":"Multi-Agent Legal Assistant","version":"1.0.0","environment":"production",
 "description":"Multi-agent legal assistant (Law / Tax / Compliance specialists)",
 "endpoints":{"ask":"POST /ask (requires X-API-Key)","health":"GET /health","ready":"GET /ready"}}

$ curl https://day12-agent-production-b2bd.up.railway.app/health
{"status":"ok","version":"1.0.0","environment":"production","uptime_seconds":25.0,
 "total_requests":2,"checks":{"llm":"mock"},
 "timestamp":"2026-06-12T10:24:22.612380+00:00"}

$ curl https://day12-agent-production-b2bd.up.railway.app/ready
{"ready":true}

# No API key → 401
$ curl -X POST https://day12-agent-production-b2bd.up.railway.app/ask \
       -H "Content-Type: application/json" -d '{"question":"hi"}'
{"detail":"Invalid or missing API key. Include header: X-API-Key: <key>"}

# With API key → multi-agent routing (law + tax + compliance, in parallel)
$ curl -X POST https://day12-agent-production-b2bd.up.railway.app/ask \
       -H "X-API-Key: my-secret-key-day12" -H "Content-Type: application/json" \
       -d '{"question": "What are the SEC and IRS penalties for offshore tax evasion?"}'
{"question":"...","answer":"## Legal Analysis\n...## Tax Analysis\n...## Regulatory Compliance Analysis\n...",
 "model":"gemini-2.0-flash","agents_consulted":["law","tax","compliance"],
 "timestamp":"2026-06-12T10:24:27.823506+00:00"}
```

## Redeploying

```bash
cd "batch02-day12_cloud_infras_and_deployment"
railway up --ci -s day12-agent
```
