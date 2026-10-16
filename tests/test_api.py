import pytest
from fastapi.testclient import TestClient

import src.app as app_module

client = TestClient(app_module.app)

FOUND = {
    "question": "q",
    "retrieved": [{"id": "a.pdf:p1:c0", "score": 0.61, "file": "a.pdf", "page": 1}],
    "chunks_used": 1,
    "found": True,
    "reason": None,
    "answer": "Answer text [1].",
    "citations": [{"n": 1, "file": "a.pdf", "page": 1}],
    "invalid_citations": [],
    "uncited": False,
}

NOT_FOUND = {
    **FOUND,
    "found": False,
    "reason": "model",
    "answer": "Not found in the documents.",
    "citations": [],
}


class FakeAPIError(Exception):
    def __init__(self, code):
        super().__init__(f"error {code}")
        self.code = code


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_query_found(monkeypatch):
    monkeypatch.setattr(app_module, "rag_answer", lambda *a, **kw: FOUND)
    r = client.post("/query", json={"question": "What is X?"})
    body = r.json()
    assert r.status_code == 200
    assert body["found"] is True
    assert body["citations"] == [{"n": 1, "file": "a.pdf", "page": 1}]


def test_query_not_found(monkeypatch):
    monkeypatch.setattr(app_module, "rag_answer", lambda *a, **kw: NOT_FOUND)
    r = client.post("/query", json={"question": "Off topic?"})
    body = r.json()
    assert r.status_code == 200
    assert body["found"] is False
    assert body["reason"] == "model"
    assert body["citations"] == []


def test_query_passes_k_and_demo_namespace(monkeypatch):
    seen = {}

    def fake(question, namespace, k):
        seen.update(question=question, namespace=namespace, k=k)
        return FOUND

    monkeypatch.setattr(app_module, "rag_answer", fake)
    client.post("/query", json={"question": "  What is X?  ", "k": 3})
    assert seen == {"question": "What is X?", "namespace": "demo", "k": 3}


@pytest.mark.parametrize(
    "payload",
    [
        {"question": ""},
        {"question": "   "},
        {"question": "x" * 501},
        {"question": "ok", "k": 0},
        {"question": "ok", "k": 11},
        {},
    ],
)
def test_query_validation(payload):
    assert client.post("/query", json=payload).status_code == 422


def test_rate_limit_maps_to_503(monkeypatch):
    def boom(*a, **kw):
        raise FakeAPIError(429)

    monkeypatch.setattr(app_module, "rag_answer", boom)
    r = client.post("/query", json={"question": "What is X?"})
    assert r.status_code == 503
    assert "rate limited" in r.json()["detail"]


def test_other_failure_maps_to_502_without_trace(monkeypatch):
    def boom(*a, **kw):
        raise RuntimeError("pinecone exploded with secret details")

    monkeypatch.setattr(app_module, "rag_answer", boom)
    r = client.post("/query", json={"question": "What is X?"})
    assert r.status_code == 502
    assert "secret" not in r.text
