# Section 3 — Cloud Deployment Options

## 3 Tier: Chọn Platform Theo Nhu Cầu

| Tier | Platform | Khi nào dùng | Thời gian deploy |
|------|----------|-------------|-----------------|
| 1 | Railway, Render | MVP, demo, học | < 10 phút |
| 2 | AWS ECS, Cloud Run | Production | 15–30 phút |
| 3 | Kubernetes | Enterprise, large-scale | Vài giờ setup |

---

## railway/ — Deploy < 5 Phút

Không cần server config. Kết nối GitHub → Auto deploy.

```
railway/
├── railway.toml        # Railway config
├── Procfile            # Define start command
├── app.py              # Agent (Railway-ready)
└── requirements.txt
```

### Các bước deploy Railway:
1. `railway login` (hoặc qua browser)
2. `railway init`
3. `railway up`
4. Nhận URL dạng `https://your-app.up.railway.app`

---

## render/ — render.yaml (Infrastructure as Code)

Định nghĩa toàn bộ infrastructure trong 1 YAML file.

```
render/
├── render.yaml         # Khai báo service, env vars, disk
└── app.py
```

---

## production-cloud-run/ — GCP Cloud Run + CI/CD

Production-grade. Tự động build và deploy khi push code.

```
production-cloud-run/
├── cloudbuild.yaml     # CI/CD pipeline
├── service.yaml        # Cloud Run service definition
└── README.md           # Hướng dẫn chi tiết
```

---

## Câu hỏi thảo luận

1. Tại sao serverless (Lambda) không phải lúc nào cũng tốt cho AI agent?
2. "Cold start" là gì? Ảnh hưởng thế nào đến UX?
3. Khi nào nên upgrade từ Railway lên Cloud Run?

---

## Trả lời

**1. Tại sao serverless (Lambda) không phải lúc nào cũng tốt cho AI agent**

- **Timeout giới hạn**: Lambda có max execution time (15 phút), nhưng nhiều thao tác AI agent (streaming response dài, multi-step tool calls, RAG pipeline) có thể vượt giới hạn hoặc cần giữ connection mở lâu.
- **Cold start nặng**: mỗi lần "lạnh", Lambda phải khởi tạo runtime, load model/client libraries (đôi khi vài trăm MB dependencies như `transformers`, `torch`) → độ trễ vài giây, tệ cho real-time chat.
- **Không giữ state/connection pool**: agent thường cần kết nối tới vector DB, Redis, LLM client — với serverless, mỗi invocation có thể là môi trường mới, khó tái sử dụng connection (tăng overhead + tốn connection limit của DB).
- **Streaming khó**: nhiều AI app cần stream token-by-token (SSE/WebSocket) — một số nền tảng serverless hỗ trợ hạn chế hoặc không hỗ trợ streaming response.
- **Chi phí**: nếu traffic ổn định/liên tục, 1 server "always-on" (Railway/Cloud Run với min-instances) có thể rẻ hơn pay-per-invocation.

→ Serverless phù hợp cho workload **ngắn, không thường xuyên, không cần latency thấp** (ví dụ: webhook xử lý batch, cron job). AI chatbot tương tác realtime thường hợp với container service (Cloud Run, Railway, ECS) hơn.

**2. "Cold start" là gì, ảnh hưởng UX**

"Cold start" là khoảng thời gian platform cần để **khởi tạo một instance/container mới** khi không có instance "warm" (đang chạy, idle) nào sẵn sàng nhận request — bao gồm: pull image, start container, khởi động runtime (Python interpreter), import dependencies, mở connection tới DB/Redis, load model...

**Ảnh hưởng UX:** request đầu tiên sau một thời gian không có traffic (ví dụ Cloud Run scale-to-zero) có thể mất thêm **vài giây đến chục giây** trước khi nhận response đầu tiên. Với chatbot, user sẽ thấy app "đứng hình"/loading lâu bất thường ngay lần hỏi đầu tiên, dễ hiểu lầm là app bị lỗi → giảm trải nghiệm, đặc biệt tệ với demo/first impression.

**Cách giảm:** giữ "min instances" ≥ 1 (luôn có 1 instance warm), dùng image nhỏ/khởi động nhanh, lazy-load các thành phần nặng, hoặc dùng platform không scale-to-zero (Railway).

**3. Khi nào nên upgrade từ Railway lên Cloud Run**

Nên chuyển khi:
- **Traffic** tăng cao/biến động mạnh và cần **auto-scale** theo request (scale từ 0 đến hàng nghìn instance theo nhu cầu thực, trả tiền theo request thực tế).
- Cần tích hợp sâu với hệ sinh thái **GCP** (IAM, VPC, Cloud SQL, Secret Manager, Pub/Sub, Cloud Logging/Monitoring) cho production thật.
- Yêu cầu **compliance/security** doanh nghiệp: VPC-SC, private networking, audit logs chi tiết, region/residency control.
- Cần **CI/CD pipeline** mạnh hơn (Cloud Build tự build & deploy mỗi push, canary/blue-green rollout).
- Quy mô đủ lớn để chi phí pay-per-request của Cloud Run rẻ hơn plan cố định của Railway.

Với prototype, demo, side-project quy mô nhỏ — Railway vẫn là lựa chọn tốt vì đơn giản và nhanh hơn nhiều.
