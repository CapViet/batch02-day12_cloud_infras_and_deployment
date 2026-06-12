"""Shared pytest fixtures and env/path setup for app tests."""
import os
import sys
from pathlib import Path

# Make both the repo root (for `utils`) and this lab dir (for `app`) importable,
# mirroring the layout produced inside the Docker image (/app/app, /app/utils).
LAB_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_DIR.parent

for path in (str(REPO_ROOT), str(LAB_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("AGENT_API_KEY", "test-api-key-123")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-123")
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "20")
os.environ.setdefault("DAILY_BUDGET_USD", "5.0")
os.environ.setdefault("REDIS_URL", "")
os.environ.setdefault("GOOGLE_API_KEY", "")
