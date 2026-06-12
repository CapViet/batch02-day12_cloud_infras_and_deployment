# ============================================================
# Dockerfile — Stateless Agent (05-scaling-reliability/production)
# Build from project root:
#   docker build -f 05-scaling-reliability/production/Dockerfile -t agent-stateless .
# ============================================================
FROM python:3.11-slim

WORKDIR /app

COPY 05-scaling-reliability/production/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY 05-scaling-reliability/production/app.py .

RUN mkdir -p utils
COPY utils/mock_llm.py utils/

EXPOSE 8000

CMD ["python", "app.py"]
