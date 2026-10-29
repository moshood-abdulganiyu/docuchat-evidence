import time

from src.sessions import is_valid_session_id, session_created_at
from src.store import get_index

MAX_AGE_SECONDS = 24 * 60 * 60


def expired_sessions(names, now=None):
    now = time.time() if now is None else now
    return [
        n
        for n in names
        if is_valid_session_id(n) and now - session_created_at(n) > MAX_AGE_SECONDS
    ]


def delete_expired(now=None):
    index = get_index()
    names = list(index.describe_index_stats().namespaces.keys())
    old = expired_sessions(names, now)
    for ns in old:
        index.delete(delete_all=True, namespace=ns)
    return {"checked": len(names), "deleted": len(old)}
