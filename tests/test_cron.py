from fastapi.testclient import TestClient

import src.app as app_module

client = TestClient(app_module.app)


def fake_delete():
    return {"checked": 3, "deleted": 1}


def test_cron_rejects_when_secret_unset(monkeypatch):
    monkeypatch.delenv("CRON_SECRET", raising=False)
    monkeypatch.setattr(app_module, "delete_expired", fake_delete)
    r = client.get("/api/cron/cleanup", headers={"Authorization": "Bearer None"})
    assert r.status_code == 401


def test_cron_rejects_missing_or_wrong_header(monkeypatch):
    monkeypatch.setenv("CRON_SECRET", "s3cret")
    monkeypatch.setattr(app_module, "delete_expired", fake_delete)
    assert client.get("/api/cron/cleanup").status_code == 401
    wrong = {"Authorization": "Bearer wrong"}
    assert client.get("/api/cron/cleanup", headers=wrong).status_code == 401


def test_cron_accepts_right_secret(monkeypatch):
    monkeypatch.setenv("CRON_SECRET", "s3cret")
    monkeypatch.setattr(app_module, "delete_expired", fake_delete)
    r = client.get("/api/cron/cleanup", headers={"Authorization": "Bearer s3cret"})
    assert r.status_code == 200
    assert r.json() == {"checked": 3, "deleted": 1}