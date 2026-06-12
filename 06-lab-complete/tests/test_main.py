"""Unit tests for the production agent API (app/main.py)."""
import pytest
from fastapi.testclient import TestClient

from app import main as main_module

API_KEY = main_module.settings.agent_api_key


@pytest.fixture()
def client():
    with TestClient(main_module.app) as test_client:
        yield test_client


def test_root(client):
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["app"] == main_module.settings.app_name
    assert "ask" in data["endpoints"]


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "uptime_seconds" in data


def test_ready(client):
    resp = client.get("/ready")
    assert resp.status_code == 200
    assert resp.json() == {"ready": True}


def test_ask_without_api_key_is_rejected(client):
    resp = client.post("/ask", json={"question": "Hello"})
    assert resp.status_code == 401


def test_ask_with_invalid_api_key_is_rejected(client):
    resp = client.post(
        "/ask", json={"question": "Hello"}, headers={"X-API-Key": "wrong-key"}
    )
    assert resp.status_code == 401


def test_ask_with_valid_api_key_succeeds(client):
    resp = client.post(
        "/ask",
        json={"question": "What is Docker?"},
        headers={"X-API-Key": API_KEY},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["question"] == "What is Docker?"
    assert data["model"] == main_module.settings.llm_model
    assert isinstance(data["answer"], str) and data["answer"]


def test_ask_rejects_empty_question(client):
    resp = client.post(
        "/ask", json={"question": ""}, headers={"X-API-Key": API_KEY}
    )
    assert resp.status_code == 422


def test_metrics_requires_auth(client):
    resp = client.get("/metrics")
    assert resp.status_code == 401

    resp = client.get("/metrics", headers={"X-API-Key": API_KEY})
    assert resp.status_code == 200
    assert "daily_cost_usd" in resp.json()


def test_rate_limit_raises_429_when_exceeded(monkeypatch):
    monkeypatch.setattr(main_module.settings, "rate_limit_per_minute", 2)
    main_module._rate_windows.clear()

    bucket = "rate-limit-test"
    main_module.check_rate_limit(bucket)
    main_module.check_rate_limit(bucket)

    with pytest.raises(main_module.HTTPException) as exc_info:
        main_module.check_rate_limit(bucket)

    assert exc_info.value.status_code == 429


def test_cost_guard_blocks_when_budget_exhausted(monkeypatch):
    monkeypatch.setattr(main_module.settings, "daily_budget_usd", 0.0)
    monkeypatch.setattr(main_module, "_daily_cost", 0.0)

    with pytest.raises(main_module.HTTPException) as exc_info:
        main_module.check_and_record_cost(input_tokens=100, output_tokens=100)

    assert exc_info.value.status_code == 503


def test_verify_api_key_returns_key_when_valid():
    assert main_module.verify_api_key(API_KEY) == API_KEY


def test_verify_api_key_rejects_missing_key():
    with pytest.raises(main_module.HTTPException) as exc_info:
        main_module.verify_api_key(None)

    assert exc_info.value.status_code == 401
