# Section 1 — Từ Localhost Đến Production

## Mục tiêu học
- Hiểu tại sao "it works on my machine" là vấn đề
- Nhận ra sự khác biệt giữa dev và production environment
- Áp dụng 4 nguyên tắc 12-factor cơ bản

---

## Ví dụ Basic — Agent "Kiểu Localhost"

```
develop/
├── app.py          # ❌ Anti-patterns: hardcode secrets, no config, no health check
├── .env.example
└── requirements.txt
```

### Chạy thử
```bash
cd basic
pip install -r requirements.txt
python app.py
# Truy cập: http://localhost:8000
```

### Những vấn đề trong code này:
1. API key hardcode trong code
2. Không có health check endpoint
3. Debug mode bật cứng
4. Không xử lý SIGTERM gracefully
5. Config không đến từ environment

---

## Ví dụ Advanced — 12-Factor Compliant Agent

```
production/
├── app.py          # ✅ Clean: config from env, health check, graceful shutdown
├── config.py       # ✅ Centralized config management
├── .env.example    # ✅ Template — không commit .env thật
└── requirements.txt
```

### Chạy thử
```bash
cd advanced
pip install -r requirements.txt
cp .env.example .env
# Sửa .env nếu cần
python app.py
```

### So sánh với Basic:

| | Basic (❌) | Advanced (✅) |
|--|-----------|--------------|
| Config | Hardcode trong code | Đọc từ env vars |
| Secrets | `api_key = "sk-abc123"` | `os.getenv("OPENAI_API_KEY")` |
| Port | Cố định `8000` | Từ `PORT` env var |
| Health check | Không có | `GET /health` |
| Shutdown | Tắt đột ngột | Graceful — hoàn thành request hiện tại |
| Logging | `print()` | Structured JSON logging |

---

## Câu hỏi thảo luận

1. Điều gì xảy ra nếu bạn push code với API key hardcode lên GitHub public?
2. Tại sao stateless quan trọng khi scale?
3. 12-factor nói "dev/prod parity" — nghĩa là gì trong thực tế?

---

## Trả lời

**1. Push code với API key hardcode lên GitHub public**

- Bot scanner (GitHub secret scanning, crawler của bên thứ 3) sẽ phát hiện và "đọc" key chỉ trong vài giây đến vài phút — kể cả khi xóa commit sau đó, key vẫn còn trong **git history**.
- Key bị lộ có thể bị người khác dùng để gọi OpenAI/Anthropic API → tài khoản bị tính phí, có thể tới hàng trăm/nghìn đô trong thời gian ngắn (bot spam request liên tục).
- Nhiều provider (OpenAI, AWS, GitHub) có cơ chế tự động **revoke** key khi phát hiện bị lộ trên public repo.
- **Cách xử lý:** revoke/rotate key ngay, xóa key khỏi toàn bộ git history (`git filter-repo`/BFG, không chỉ commit mới nhất), thêm `.env` vào `.gitignore`, đọc key từ environment variable hoặc secret manager.

**2. Tại sao stateless quan trọng khi scale**

- Khi scale ngang (nhiều instance), load balancer có thể route mỗi request của cùng 1 user tới **một instance khác nhau** mỗi lần.
- Nếu state (conversation history, session, counters) lưu **trong memory** của 1 instance, request tiếp theo rơi vào instance khác sẽ không thấy state đó → mất dữ liệu, lỗi logic, rate-limit/cost-guard bị "reset" sai.
- Stateless = lưu state ở nơi **dùng chung** (Redis, database) → mọi instance đọc/viết cùng nguồn, có thể start/stop/scale/restart tự do mà không ảnh hưởng người dùng. Đây là điều kiện tiên quyết để load balancing và auto-scaling hoạt động đúng.

**3. "Dev/prod parity" nghĩa là gì trong thực tế**

12-Factor khuyến nghị giữ môi trường dev và production **giống nhau càng nhiều càng tốt**:

- **Time gap nhỏ:** code viết xong nên được deploy production sớm (vài giờ/ngày, không phải vài tuần).
- **Personnel gap nhỏ:** người viết code cũng tham gia deploy/giám sát, không tách biệt hoàn toàn dev và ops.
- **Tools gap nhỏ:** dùng cùng loại backing service ở cả 2 môi trường — ví dụ Redis thật (qua Docker) trong dev, không dùng in-memory dict rồi đổi sang Redis ở production; cùng Python version, cùng base image Docker.

Mục tiêu: giảm tối đa class bug "chạy được trên máy tôi nhưng fail trên production" do khác biệt môi trường.
