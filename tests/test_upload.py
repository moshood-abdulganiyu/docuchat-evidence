import pytest
from fastapi.testclient import TestClient

import src.app as appmod
from src.pdf_pages import extract_pages
from src.sessions import MAX_BYTES, is_valid_session_id, new_session_id

client = TestClient(appmod.app)
TEXT = "Retrieval augmented generation cites the page it used for every answer given."


def make_pdf(text: str = TEXT) -> bytes:
    stream = f"BT /F1 12 Tf 72 700 Td ({text}) Tj ET".encode()
    objs = [
        b"<</Type/Catalog/Pages 2 0 R>>",
        b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        (
            b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R"
            b"/Resources<</Font<</F1 5 0 R>>>>>>"
        ),
        b"<</Length %d>>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    ]

    out, offsets = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += b"trailer\n<</Size %d/Root 1 0 R>>\nstartxref\n%d\n%%%%EOF" % (
        len(objs) + 1,
        xref,
    )
    return out


@pytest.fixture
def store(monkeypatch):
    """namespace -> list of file names; stands in for Pinecone."""
    db: dict[str, list[dict]] = {}

    def fake_index(pages, namespace, max_chunks=None):
        db.setdefault(namespace, []).extend(pages)
        return len(pages) * 3

    def fake_list(namespace):
        return {p["file"] for p in db.get(namespace, [])}

    def fake_rag(question, namespace="demo", k=5):
        hits = db.get(namespace, [])
        return {
            "question": question,
            "retrieved": [],
            "chunks_used": len(hits),
            "found": bool(hits),
            "reason": None if hits else "gate",
            "answer": hits[0]["file"] if hits else "Not found in the documents.",
            "citations": [],
            "invalid_citations": [],
            "uncited": False,
        }

    monkeypatch.setattr(appmod, "index_pages", fake_index)
    monkeypatch.setattr(appmod, "list_session_files", fake_list)
    monkeypatch.setattr(appmod, "rag_answer", fake_rag)
    return db


def post(name="a.pdf", data=None, sid=None):
    data = make_pdf() if data is None else data
    return client.post(
        "/upload",
        files={"file": (name, data, "application/pdf")},
        data={"session_id": sid} if sid else {},
    )


def test_session_id_format():
    sid = new_session_id()
    assert is_valid_session_id(sid)
    assert not is_valid_session_id("demo")
    assert not is_valid_session_id("sess_1_abc")


def test_extract_pages_real_pdf():
    pages = extract_pages(make_pdf(), "a.pdf")
    assert len(pages) == 1 and pages[0]["page"] == 1


def test_upload_happy_path(store):
    r = post()
    assert r.status_code == 200
    body = r.json()
    assert is_valid_session_id(body["session_id"])
    assert body["files_in_session"] == 1 and body["pages"] == 1


def test_not_a_pdf(store):
    assert post(data=b"hello world").status_code == 422


def test_not_pdf_extension(store):
    assert post(name="a.txt").status_code == 422


def test_too_large(store):
    assert post(data=b"%PDF-" + b"0" * MAX_BYTES).status_code == 413


def test_duplicate_name(store):
    sid = post().json()["session_id"]
    assert post(sid=sid).status_code == 409


def test_sixth_file_rejected(store):
    sid = post("f0.pdf").json()["session_id"]
    for i in range(1, 5):
        assert post(f"f{i}.pdf", sid=sid).status_code == 200
    assert post("f5.pdf", sid=sid).status_code == 409


def test_scanned_pdf_no_text(store, monkeypatch):
    monkeypatch.setattr(appmod, "extract_pages", lambda data, name: [])
    assert post().status_code == 422


def test_invalid_session_id_upload(store):
    assert post(sid="demo").status_code == 422


def test_invalid_session_id_query(store):
    r = client.post("/query", json={"question": "hi", "session_id": "demo"})
    assert r.status_code == 422


def test_cross_session_isolation(store):
    a = post("a.pdf").json()["session_id"]
    b = post("b.pdf").json()["session_id"]
    ra = client.post("/query", json={"question": "x", "session_id": a}).json()
    rb = client.post("/query", json={"question": "x", "session_id": b}).json()
    demo = client.post("/query", json={"question": "x"}).json()
    assert ra["answer"] == "a.pdf" and rb["answer"] == "b.pdf"
    assert demo["found"] is False  # demo namespace never sees session data
