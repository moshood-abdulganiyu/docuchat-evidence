import time

from src.cleanup import expired_sessions
from src.sessions import new_session_id


def test_only_old_valid_sessions_expire():
    old = "sess_1000000000_" + "a" * 16
    fresh = new_session_id()
    now = time.time()
    assert expired_sessions(["demo", old, fresh, "junk"], now) == [old]
