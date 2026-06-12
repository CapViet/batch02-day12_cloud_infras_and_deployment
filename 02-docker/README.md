# Section 2 — Docker: Đóng Gói Agent Thành Container

## Mục tiêu học
- Hiểu container là gì và tại sao cần nó
- Viết Dockerfile đúng cách (single vs multi-stage)
- Dùng Docker Compose để chạy multi-service stack
- Tối ưu image size xuống dưới 500 MB

---

## Ví dụ Basic — Dockerfile Đơn Giản

```
develop/
├── app.py
├── Dockerfile          # Single-stage, dễ hiểu
├── .dockerignore
└── requirements.txt
```

### Chạy thử
```bash
# IMPORTANT: Build from project root!
cd ../..  # Go to project root

# Build image
docker build -f 02-docker/develop/Dockerfile -t agent-develop .

# Xem size
docker images agent-develop

# Chạy container
docker run -p 8000:8000 agent-develop

# Test
curl http://localhost:8000/health
```

---

## Ví dụ Advanced — Multi-Stage + Docker Compose

```
production/
├── app.py
├── Dockerfile              # Multi-stage build → image nhỏ hơn nhiều
├── docker-compose.yml      # Full stack: agent + vector store + redis
├── nginx/
│   └── nginx.conf          # Reverse proxy
├── .dockerignore
└── requirements.txt
```

### Chạy thử
```bash
# From project root
cd ../..  # if not already there

# Khởi động toàn bộ stack (1 lệnh!)
docker compose -f 02-docker/production/docker-compose.yml up

# Xem các service đang chạy
docker compose -f 02-docker/production/docker-compose.yml ps

# Test agent qua Nginx
curl http://localhost/health

# Dừng toàn bộ
docker compose -f 02-docker/production/docker-compose.yml down
```

### So sánh image size:

```bash
# Basic vs Advanced
docker images | grep agent
# agent-basic    ~  800 MB  ← python:3.11 base
# agent-advanced ~  160 MB  ← python:3.11-slim + multi-stage
```

---

## Lý thuyết: Tại Sao Multi-Stage?

```dockerfile
# Stage 1: Builder — có đầy đủ tools để compile deps
FROM python:3.11 AS builder   # 1 GB
RUN pip install ...            # thêm deps vào layer này

# Stage 2: Runtime — chỉ copy những gì cần chạy
FROM python:3.11-slim          # 150 MB ← bắt đầu từ image sạch
COPY --from=builder ...        # copy chỉ /site-packages
```

**Kết quả:** Final image chỉ có runtime, không có pip, không có build tools → nhỏ và an toàn hơn.

---

## Câu hỏi thảo luận

1. Tại sao `COPY requirements.txt .` rồi `RUN pip install` TRƯỚC khi `COPY . .`?
2. `.dockerignore` nên chứa những gì? Tại sao `venv/` và `.env` quan trọng?
3. Nếu agent cần đọc file từ disk, làm sao mount volume vào container?

---

## Trả lời

**1. Tại sao `COPY requirements.txt .` + `RUN pip install` TRƯỚC `COPY . .`**

Docker build theo **layer cache**: mỗi instruction (`COPY`, `RUN`, ...) tạo ra 1 layer, và layer chỉ rebuild lại nếu input của nó thay đổi.

- Nếu copy `requirements.txt` và `pip install` trước, sau đó mới `COPY . .`: khi bạn sửa code (không đổi dependencies), layer `pip install` vẫn được **cache** → build lại chỉ tốn vài giây (chỉ copy code mới).
- Nếu `COPY . .` trước rồi mới `pip install`: bất kỳ thay đổi nhỏ trong code cũng làm layer đó đổi → invalidate cache của layer `pip install` phía sau → phải cài lại **toàn bộ dependencies** mỗi lần build, rất chậm (có thể mất vài phút mỗi lần).

**2. `.dockerignore` nên chứa gì, và vì sao `venv/`, `.env` quan trọng**

Nên loại trừ:
```
__pycache__/
*.pyc
.git/
.venv/
venv/
.env
.env.*
!.env.example
*.md
tests/
.DS_Store
```

- **`venv/` / `.venv/`**: virtual env chứa hàng trăm MB packages đã cài cho OS/arch của máy dev — copy vào image sẽ làm image phình to không cần thiết, và có thể **không tương thích** với OS/arch base image trong container (binary compiled khác platform). Docker tự `pip install` lại trong build, nên không cần copy venv.
- **`.env`**: chứa **secrets thật** (API key, password, JWT secret). Nếu copy vào image, secret sẽ nằm vĩnh viễn trong layer của image — bất kỳ ai pull được image (registry) đều có thể `docker history`/`docker save` để lấy ra secret. Secrets phải truyền vào **lúc runtime** qua biến môi trường (`docker run -e ...`, `docker-compose environment:`, hoặc secret manager của cloud platform), không bao giờ bake vào image.

**3. Mount volume để agent đọc file từ disk**

Dùng flag `-v` (docker run) hoặc `volumes:` (docker-compose):

```bash
docker run -v $(pwd)/data:/app/data -p 8000:8000 my-agent
```

```yaml
services:
  agent:
    build: .
    volumes:
      - ./data:/app/data        # bind mount: thư mục host ↔ container
      - redis-data:/data        # named volume: do Docker quản lý, persist độc lập container

volumes:
  redis-data:
```

Khác với `COPY` (bake file vào image lúc build — immutable, chỉ thấy snapshot lúc build), volume mount diễn ra **lúc container chạy**: file trên host và trong container được đồng bộ 2 chiều, dữ liệu vẫn tồn tại sau khi container bị xóa — phù hợp cho data cần persist (DB, logs, uploaded files) hoặc khi cần live-reload code lúc dev.
