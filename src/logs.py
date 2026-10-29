import json
import logging

log = logging.getLogger("docuchat")


def event(name: str, **fields) -> None:
    log.info(json.dumps({"event": name, **fields}, default=str))