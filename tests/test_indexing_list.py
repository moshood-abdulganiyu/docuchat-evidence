from types import SimpleNamespace

import src.indexing as indexing


class FakeIndex:
    """Mimics index.list(): yields pages, each page a list of ids."""

    def __init__(self, pages):
        self.pages = pages

    def list(self, **kwargs):
        yield from self.pages


def item(vid):
    return SimpleNamespace(id=vid)


def test_list_session_files_reads_list_items(monkeypatch):
    pages = [[item("a.pdf:p1:c0"), item("a.pdf:p2:c0")], [item("b.pdf:p1:c0")]]
    monkeypatch.setattr(indexing, "get_index", lambda: FakeIndex(pages))
    assert set(indexing.list_session_files("sess_x")) == {"a.pdf", "b.pdf"}


def test_list_session_files_still_reads_plain_strings(monkeypatch):
    pages = [["a.pdf:p1:c0", "b.pdf:p3:c1"]]
    monkeypatch.setattr(indexing, "get_index", lambda: FakeIndex(pages))
    assert set(indexing.list_session_files("sess_x")) == {"a.pdf", "b.pdf"}