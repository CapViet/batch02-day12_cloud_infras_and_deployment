# Section 4 — API Gateway & Security

## Mục tiêu học
- Hiểu tại sao cần lớp bảo vệ trước agent
- Implement API Key authentication
- Implement JWT authentication (nâng cao)
- Rate limiting và cost protection

---

## Ví dụ Basic — API Key Authentication

```
develop/
├── app.py              # Agent với API Key auth
├── test_auth.py        # Test script
└── requirements.txt
```

### Chạy thử
```bash
cd basic
pip install -r requirements.txt
AGENT_API_KEY=my-secret-key python app.py

# Test với key hợp lệ
curl -H "X-API-Key: my-secret-key" http://localhost:8000/ask \
     -X POST -H "Content-Type: application/json" \
     -d '{"question": "hello"}'

# Test không có key → 401
curl http://localhost:8000/ask -X POST \
     -H "Content-Type: application/json" \
     -d '{"question": "hello"}'
```

---

## Ví dụ Advanced — JWT + Rate Limiting + Cost Guard

```
production/
├── app.py              # Full security stack
├── auth.py             # JWT token logic
├── rate_limiter.py     # In-memory rate limiter
├── cost_guard.py       # Token budget và spending alerts
├── test_advanced.py    # Test suite
└── requirements.txt
```

### Chạy thử
```bash
cd advanced
pip install -r requirements.txt
python app.py

# Lấy JWT token
curl -X POST http://localhost:8000/auth/token \
     -H "Content-Type: application/json" \
     -d '{"username": "student", "password": "demo123"}'

# Dùng token
curl -H "Authorization: Bearer <token>" \
     http://localhost:8000/ask \
     -X POST -H "Content-Type: application/json" \
     -d '{"question": "what is docker?"}'

# Test rate limit: spam 20 requests liên tiếp
python test_advanced.py --test rate-limit
```

---

## Luồng bảo vệ

```
Request
  → Auth Check (401 nếu fail)
  → Rate Limit (429 nếu vượt quota)
  → Input Validation (422 nếu invalid)
  → Cost Check (402 nếu hết budget)
  → Agent (200 nếu mọi thứ OK)
```

---

## Câu hỏi thảo luận

1. Khi nào nên dùng API Key vs JWT vs OAuth2?
2. Rate limit nên đặt bao nhiêu request/phút cho một AI agent?
3. Nếu API key bị lộ, bạn phát hiện và xử lý như thế nào?

---

## Trả lời

**1. Khi nào dùng API Key vs JWT vs OAuth2**

- **API Key**: đơn giản nhất, phù hợp **service-to-service** (machine-to-machine) hoặc khi cấp quyền truy cập cho 1 đối tác/khách hàng cụ thể (mỗi key = 1 client). Không chứa thông tin về user, không có expiry tự nhiên — phù hợp khi số lượng client ít và bạn kiểm soát việc cấp/rotate key thủ công.
- **JWT**: phù hợp khi cần **authentication có thông tin user** (claims: user_id, role, expiry) trong một hệ thống có login flow (username/password → token). Stateless — server verify token bằng signature mà không cần query DB mỗi request, có thời hạn rõ ràng (`exp`), dễ kèm thêm thông tin phân quyền (scope/role).
- **OAuth2**: phù hợp khi cần **ủy quyền (authorization) cho bên thứ ba** truy cập tài nguyên thay mặt user (ví dụ "Login with Google/GitHub"), hoặc hệ thống multi-tenant/SaaS cần nhiều scope khác nhau, refresh token, và tách biệt rõ "ai đang đăng nhập" vs "app nào được phép làm gì".

Quy tắc chung: API Key cho nội bộ/đối tác cố định, JWT cho user login trong app của chính bạn, OAuth2 khi tích hợp identity provider bên ngoài hoặc phân quyền phức tạp.

**2. Rate limit hợp lý cho AI agent**

Không có số tuyệt đối — phụ thuộc cost của LLM call và mục đích sử dụng, nhưng tham khảo:

- **Demo/học tập, free tier**: ~10–20 request/phút/user — đủ cho hội thoại bình thường, ngăn spam/abuse cơ bản (giống `RATE_LIMIT_PER_MINUTE=20` trong lab).
- **Production, user trả phí**: có thể nâng lên 60–100 req/phút, hoặc tier hóa theo plan (free/pro/enterprise).
- Nên kết hợp **2 lớp**: rate limit theo request/phút (chống spam, DoS) **+** cost guard theo token/ngày hoặc tháng (chống "burn tiền" dù request nhỏ nhưng câu hỏi/câu trả lời rất dài).

**3. Nếu API key bị lộ — phát hiện và xử lý**

**Phát hiện:**
- Theo dõi `/metrics` hoặc dashboard: số request, chi phí (`daily_cost_usd`) tăng đột biến bất thường, hoặc IP/client lạ gọi liên tục.
- Log structured (JSON) ghi lại client IP, timestamp — dễ phát hiện pattern lạ (request dồn dập từ 1 IP không quen).
- GitHub secret scanning / push protection nếu key bị commit nhầm vào repo.

**Xử lý:**
1. **Revoke key cũ ngay** (set lại `AGENT_API_KEY` mới trong env/secret manager → key cũ ngừng hoạt động lập tức nhờ comparing trực tiếp với `settings.agent_api_key`).
2. **Generate & phân phối key mới** cho client hợp lệ qua kênh an toàn.
3. Nếu key từng bị commit vào git: xóa khỏi history (BFG/`git filter-repo`), không chỉ revert commit.
4. Review log/metrics để đánh giá thiệt hại (bao nhiêu request/cost phát sinh từ key bị lộ).
5. Bổ sung biện pháp phòng ngừa: secret scanning trong CI, không log full API key (chỉ log `key[:8]` như trong `06-lab-complete`), rotate key định kỳ.
