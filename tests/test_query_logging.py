from fastapi.testclient import TestClient

from src import app as app_module

client = TestClient(app_module.app)

QUESTION = "What secret topic does the paper cover?"


def fake_result(found=True):
    return {
        "answer": "Private answer text [1]."
        if found
        else "Not found in the documents.",
        "found": found,
        "reason": None if found else "model",
        "citations": [{"n": 1, "file": "a.pdf", "page": 2}] if found else [],
        "uncited": False,
        "retrieved": [
            {"id": "a.pdf:p2:c0", "score": 0.61234, "file": "a.pdf", "page": 2},
            {"id": "a.pdf:p3:c1", "score": 0.4, "file": "a.pdf", "page": 3},
        ],
    }


def capture(monkeypatch):
    events = []
    monkeypatch.setattr(
        app_module, "event", lambda name, **fields: events.append((name, fields))
    )
    return events


def test_query_logs_retrieval_fields_without_text(monkeypatch):
    events = capture(monkeypatch)
    monkeypatch.setattr(app_module, "rag_answer", lambda *a, **kw: fake_result())

    res = client.post("/query", json={"question": QUESTION})

    assert res.status_code == 200
    fields = dict(events)["query"]
    assert fields["mode"] == "demo"
    assert fields["found"] is True
    assert fields["retrieved"] == 2
    assert fields["top_score"] == 0.612
    assert fields["cited"] == 1
    assert fields["rewritten"] is False
    assert "Private answer text" not in str(events)
    assert QUESTION not in str(events)


def test_query_logs_error_type_without_text(monkeypatch):
    events = capture(monkeypatch)

    def boom(*args, **kwargs):
        raise RuntimeError(f"failed on {QUESTION}")

    monkeypatch.setattr(app_module, "rag_answer", boom)

    res = client.post("/query", json={"question": QUESTION})

    assert res.status_code == 502
    fields = dict(events)["query_error"]
    assert fields["error_type"] == "RuntimeError"
    assert fields["error_code"] is None
    assert QUESTION not in str(events)
