import pytest
from fastapi.testclient import TestClient

import src.app as appmod
import src.rewrite as rw
from src.models import Turn

client = TestClient(appmod.app)


def fake_rag(question, namespace="demo", k=5):
    return {
        "question": question,
        "retrieved": [],
        "chunks_used": 0,
        "found": True,
        "reason": None,
        "answer": "ans: " + question,
        "citations": [],
        "invalid_citations": [],
        "uncited": False,
    }


@pytest.fixture(autouse=True)
def _fake_rag(monkeypatch):
    monkeypatch.setattr(appmod, "rag_answer", fake_rag)


def msgs(n):
    return [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"m{i}"}
        for i in range(n)
    ]


def test_no_history_skips_rewrite(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("rewrite must not run without history")

    monkeypatch.setattr(appmod, "rewrite_question", boom)
    r = client.post("/query", json={"question": "What is X?"})
    assert r.status_code == 200
    assert r.json()["rewritten_question"] is None
    assert r.json()["answer"] == "ans: What is X?"


def test_rewritten_question_is_used(monkeypatch):
    monkeypatch.setattr(appmod, "rewrite_question", lambda q, h: "standalone q")
    r = client.post("/query", json={"question": "and that one?", "history": msgs(2)})
    assert r.json()["answer"] == "ans: standalone q"
    assert r.json()["rewritten_question"] == "standalone q"


def test_history_capped_at_6(monkeypatch):
    seen = {}

    def spy(q, h):
        seen["h"] = h
        return q

    monkeypatch.setattr(appmod, "rewrite_question", spy)
    client.post("/query", json={"question": "q", "history": msgs(8)})
    assert len(seen["h"]) == 6
    assert seen["h"][-1].content == "m7"


def test_history_over_20_rejected():
    r = client.post("/query", json={"question": "q", "history": msgs(21)})
    assert r.status_code == 422


def test_bad_role_rejected():
    bad = [{"role": "system", "content": "x"}]
    r = client.post("/query", json={"question": "q", "history": bad})
    assert r.status_code == 422


def test_rewrite_failure_falls_back(monkeypatch):
    def fail(prompt, system=None):
        raise RuntimeError("down")

    monkeypatch.setattr(rw, "generate", fail)
    assert rw.rewrite_question("q", [Turn(role="user", content="hi")]) == "q"


def test_rewrite_keeps_first_line(monkeypatch):
    monkeypatch.setattr(rw, "generate", lambda p, system=None: "  What is X?\nextra")
    assert rw.rewrite_question("q", [Turn(role="user", content="hi")]) == "What is X?"
