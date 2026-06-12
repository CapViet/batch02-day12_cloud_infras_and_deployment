# Solution — Đáp án Code Lab (Part 1 → 5)

Đáp án thực hành cho `CODE_LAB.md` Part 1–5. Các câu hỏi thảo luận chi tiết
(lý thuyết) đã được trả lời trực tiếp trong từng `README.md` tương ứng
(section **"Trả lời"**): [01](01-localhost-vs-production/README.md),
[02](02-docker/README.md), [03](03-cloud-deployment/README.md),
[04](04-api-gateway/README.md). File này tập trung vào các bài thực hành
(exercise) và kết quả đo được.

---

## Part 1 — Localhost vs Production

### Exercise 1.1 — Anti-patterns trong `01-localhost-vs-production/develop/app.py`

5 vấn đề chính:
1. **API key hardcode** trong source code (`api_key = "sk-..."`).
2. **Port cố định** (`8000`) — không đọc từ `PORT` env var (bắt buộc trên Railway/Render).
3. **Debug mode bật cứng** (`debug=True`) — lộ stack trace, traceback chi tiết cho client.
4. **Không có health check endpoint** — platform không biết container còn sống không.
5. **Không xử lý SIGTERM** — container bị kill đột ngột, request đang chạy bị mất, không graceful shutdown.

### Exercise 1.3 — So sánh Basic vs Advanced

| Feature | Basic (`develop/`) | Advanced (`production/`) | Tại sao quan trọng? |
|---|---|---|---|
| Config | Hardcode trong code | Đọc từ env vars (`config.py`, dataclass `Settings`) | Đổi secret/port không cần build lại image; 12-factor "config" |
| Secrets | `api_key = "sk-abc123"` | `os.getenv("OPENAI_API_KEY")` | Tránh leak secret qua git history |
| Port | Cố định `8000` | `PORT` env var | Railway/Render tự gán port động |
| Health check | Không có | `GET /health` | Platform tự restart container chết |
| Readiness | Không có | `GET /ready` | Load balancer không route traffic khi app chưa sẵn sàng |
| Logging | `print()` | Structured JSON (`logging` + `json.dumps`) | Dễ parse bởi log aggregator (Datadog, CloudWatch...) |
| Shutdown | Tắt đột ngột | `signal.signal(SIGTERM, ...)` + `timeout_graceful_shutdown` | Hoàn thành request hiện tại trước khi container bị xoá |

---

## Part 2 — Docker Containerization

### Exercise 2.1 — Đọc `02-docker/develop/Dockerfile`

1. **Base image:** `python:3.11` (full image, không phải `-slim`).
2. **Working directory:** `/app`.
3. **Tại sao `COPY requirements.txt` trước `COPY . .`:** để tận dụng Docker layer cache — nếu code thay đổi nhưng dependencies không đổi, layer `pip install` được cache lại, build nhanh hơn nhiều (xem chi tiết trong [02-docker/README.md → Trả lời câu 1](02-docker/README.md)).
4. **CMD vs ENTRYPOINT:** `CMD` định nghĩa command mặc định, có thể bị override hoàn toàn khi `docker run <image> <other-cmd>`. `ENTRYPOINT` cố định executable, `CMD` (nếu có) chỉ cung cấp argument mặc định cho `ENTRYPOINT`. Dự án này dùng `CMD` để có thể dễ dàng override khi debug (`docker run -it my-agent /bin/sh`).

### Exercise 2.2 / 2.3 — Build & so sánh image size

```bash
docker build -f 02-docker/develop/Dockerfile -t my-agent:develop .
docker build -f 02-docker/production/Dockerfile -t my-agent:advanced .
docker images | grep my-agent
```

Kết quả đo thực tế trên máy:

| Image | Base | Size |
|---|---|---|
| `my-agent:develop` (single-stage, `python:3.11`) | `python:3.11` | **~1.66 GB** |
| `my-agent:advanced` (multi-stage, `python:3.11-slim`) | `python:3.11-slim` | **~236 MB** |

→ Multi-stage build giảm size **~86%** — vì stage runtime không còn build tools
(gcc, headers) và base `-slim` đã nhỏ hơn `python:3.11` đầy đủ ~850 MB.

### Exercise 2.4 — Docker Compose stack

`docker-compose.yml` (trong `02-docker/production/`) khởi động:
- **agent** (FastAPI app, container chính)
- **redis** (state lưu ngoài, phục vụ stateless design ở Part 5)
- **nginx** (reverse proxy / load balancer phía trước agent)

Luồng: `client → nginx (port 80) → agent (port 8000) → redis`.
`agent` đọc/viết session vào `redis` qua `REDIS_URL`; `nginx` route mọi request
tới `agent` (và có thể load-balance nhiều instance `agent` khi scale).

---

## Part 3 — Cloud Deployment

### Exercise 3.1/3.2 — Deploy Railway / Render

Đã deploy thành công lên **Railway** — project `day12-agent`. Xem
[`06-lab-complete/DEPLOYMENT.md`](06-lab-complete/DEPLOYMENT.md) (hoặc mục
"Deployment" cuối file này) cho URL thật và kết quả test.

So sánh `render.yaml` vs `railway.toml`:

| | `railway.toml` | `render.yaml` |
|---|---|---|
| Phạm vi | Chỉ build/deploy config (builder, start command, healthcheck) | Infrastructure-as-code đầy đủ: service type, plan, env vars, disk, region |
| Build | Thường trỏ tới Dockerfile | Có thể dùng Dockerfile hoặc native runtime (`env: python`) |
| Env vars | Set qua CLI/dashboard, không khai báo trong file | Khai báo trực tiếp trong YAML (`envVars:`), kể cả `sync: false` cho secrets |
| Triết lý | Railway tối giản, nhiều default tự động | Render khai báo rõ ràng, gần với Terraform/IaC hơn |

---

## Part 4 — API Security

### Exercise 4.1 — API Key authentication (`04-api-gateway/develop/app.py`)

- API key được check trong dependency `verify_api_key` (FastAPI `Security(APIKeyHeader)`),
  so sánh trực tiếp với `settings.agent_api_key`.
- Nếu sai/thiếu key → `401 Unauthorized` với message hướng dẫn header cần dùng.
- **Rotate key:** đổi giá trị `AGENT_API_KEY` trong env/secret manager và redeploy —
  key cũ bị từ chối ngay lập tức (so sánh trực tiếp, không cache).

### Exercise 4.2 — JWT flow (`04-api-gateway/production/auth.py`)

1. Client gọi `POST /auth/token` với `username`/`password` → server kiểm tra
   trong `DEMO_USERS`, nếu hợp lệ → ký JWT (HS256, `JWT_SECRET`, có `exp`).
2. Client gửi `Authorization: Bearer <token>` ở các request tiếp theo.
3. Server `verify_token()` decode + kiểm tra signature & `exp` — nếu hợp lệ,
   trả về `user_id`/`role` từ claims (không cần query DB mỗi request — stateless).
4. Token hết hạn → `401`, client phải xin token mới.

### Exercise 4.3 — Rate limiting (`04-api-gateway/production/rate_limiter.py`)

- **Algorithm:** Sliding Window Counter — mỗi user có 1 `deque` timestamps;
  mỗi request loại bỏ timestamp cũ hơn `window_seconds` (60s), rồi so sánh
  `len(window)` với `max_requests`.
- **Limit:** mặc định `RATE_LIMIT_PER_MINUTE=20` (cấu hình qua env, xem
  [04-api-gateway/README.md → Trả lời câu 2](04-api-gateway/README.md)).
- **Bypass cho admin:** thêm role/flag trong JWT claims (`role: "admin"`) và
  skip `check()` trong dependency nếu `role == "admin"` — không hardcode
  trong rate limiter mà kiểm tra ở tầng dependency injection.
- Khi vượt limit → `429 Too Many Requests` kèm header `Retry-After: 60`.

### Exercise 4.4 — Cost guard (`04-api-gateway/production/cost_guard.py`)

`CostGuard` track `UsageRecord` (input/output tokens, request count) theo
`user_id` + ngày (`day`), tính `total_cost_usd` dựa trên giá per-1K-token.
Khi `total_cost_usd >= daily_budget_usd` → raise `503` (hoặc `402 Payment
Required` cho user-level budget). Reset tự động khi `day` đổi (so sánh
`time.strftime("%Y-%m-%d")` với `record.day`).

Pattern Redis-based (cho multi-instance, theo gợi ý trong `CODE_LAB.md`):

```python
def check_budget(user_id: str, estimated_cost: float) -> bool:
    month_key = datetime.now().strftime("%Y-%m")
    key = f"budget:{user_id}:{month_key}"
    current = float(r.get(key) or 0)
    if current + estimated_cost > 10:
        return False
    r.incrbyfloat(key, estimated_cost)
    r.expire(key, 32 * 24 * 3600)
    return True
```

→ Dùng Redis (không phải biến in-memory) để budget được chia sẻ giữa nhiều
instance khi scale ngang (xem Part 5).

---

## Part 5 — Scaling & Reliability

### Exercise 5.1 — Health & readiness checks

```python
@app.get("/health")
def health():
    """Liveness probe — process còn sống không?"""
    return {"status": "ok"}

@app.get("/ready")
def ready():
    """Readiness probe — sẵn sàng nhận traffic không?"""
    if not _is_ready:          # set True khi lifespan startup hoàn tất
        raise HTTPException(503, "Not ready")
    return {"ready": True}
```

`/health` luôn trả 200 nếu process còn chạy (dùng cho restart policy).
`/ready` trả 503 trong lúc app chưa init xong (kết nối DB/Redis, load
model...) — load balancer sẽ không route traffic tới instance này cho tới
khi `/ready` trả 200. Đã implement trong `06-lab-complete/app/main.py`.

### Exercise 5.2 — Graceful shutdown

```python
def _handle_signal(signum, _frame):
    logger.info(json.dumps({"event": "signal", "signum": signum}))

signal.signal(signal.SIGTERM, _handle_signal)
```

kết hợp với `uvicorn.run(..., timeout_graceful_shutdown=30)`: khi container
orchestrator gửi `SIGTERM`, uvicorn ngừng nhận **request mới** nhưng cho
request đang xử lý tối đa 30s để hoàn thành trước khi exit — request đang
chạy không bị cắt ngang.

### Exercise 5.3 — Stateless design

**Anti-pattern:**
```python
conversation_history = {}  # ❌ trong memory — mất khi instance khác xử lý request
```

**Correct (Redis):**
```python
def save_session(user_id, history):
    r.set(f"session:{user_id}", json.dumps(history), ex=3600)

def load_session(user_id):
    data = r.get(f"session:{user_id}")
    return json.loads(data) if data else []
```

Lý do: khi scale ra N instance, load balancer route request của cùng 1 user
tới các instance khác nhau theo từng request. State lưu trong memory của 1
instance sẽ không tồn tại ở instance khác → mất conversation, rate-limit /
cost-guard counter bị "reset" sai. Lưu trong Redis (shared backing store) thì
mọi instance đọc/viết cùng nguồn — instance có thể bị restart/scale tự do.
Implementation tham khảo: `05-scaling-reliability/production/app.py`
(`save_session` / `load_session` / `append_to_history`, với `USE_REDIS`
fallback về in-memory dict khi chạy dev không có Redis).

### Exercise 5.4 — Load balancing

```bash
docker compose up --scale agent=3
```

khởi động 3 container `agent`; `nginx` (reverse proxy, `nginx.conf`) nhận
request ở port 80 và phân tán (round-robin theo default) tới 3 upstream
`agent:8000`. Nếu 1 instance bị kill, Docker Compose/`nginx` health check
loại nó khỏi pool, traffic chuyển sang 2 instance còn lại — minh chứng tại
sao **stateless** (Exercise 5.3) là điều kiện bắt buộc để load balancing hoạt
động đúng (mỗi request có thể rơi vào instance khác nhau).

---

## Deployment (Part 2 của checklist)

Project được productionize và deploy: **Multi-Agent Legal Assistant**
(`06-lab-complete/`) — bản productionized của hệ multi-agent
`law_agent` / `tax_agent` / `compliance_agent` từ Day 09
(`Batch02-Day9_Multi-Agent_MCP-A2A`).

Chi tiết kiến trúc, các bước productionization đã áp dụng, và **public API
URL** xem tại [`06-lab-complete/DEPLOYMENT.md`](06-lab-complete/DEPLOYMENT.md).
