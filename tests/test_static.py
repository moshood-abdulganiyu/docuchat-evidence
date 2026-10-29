from fastapi.testclient import TestClient

import src.app as appmod

client = TestClient(appmod.app)


def test_index_served():
    r = client.get("/")
    assert r.status_code == 200
    assert "DocuChat Evidence" in r.text


def test_assets_served():
    assert client.get("/app.js").status_code == 200
    assert client.get("/style.css").status_code == 200


def test_api_routes_not_shadowed():
    assert client.get("/health").json() == {"status": "ok"}
