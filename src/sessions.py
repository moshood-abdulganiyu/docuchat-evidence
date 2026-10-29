import re
import secrets
import time

MAX_FILES = 5
MAX_BYTES = 4 * 1024 * 1024
MAX_CHUNKS_PER_FILE = 800  # guess; revise after measuring embed time

_SESSION_RE = re.compile(r"^sess_(\d{10})_([0-9a-f]{16})$")


def new_session_id() -> str:
    return f"sess_{int(time.time())}_{secrets.token_hex(8)}"


def is_valid_session_id(value: str) -> bool:
    return bool(_SESSION_RE.fullmatch(value))


def session_created_at(session_id: str) -> int:
    """Unix timestamp inside the id. The step 12 cron job uses this."""
    m = _SESSION_RE.fullmatch(session_id)
    if not m:
        raise ValueError("invalid session id")
    return int(m.group(1))
