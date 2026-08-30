"""Recent events, for the console to show without touching journalctl."""

import re
import threading
import time
from collections import deque

DEFAULT_CAPACITY = 100

# Anything sitting in a `t=` parameter, whatever it is.
_TOKEN_PARAM = re.compile(r"(?<=\bt=)[^\s&\"']+")


def _redact(message: str, secret: str | None) -> str:
    """Strip the pairing token.

    The console renders this log right next to the QR code, so a token
    that leaked into a log line would defeat the barrier the whole page
    is built around.

    Matching by shape does not work here: the token is twelve characters
    of the URL-safe alphabet, and so is the word "disconnected". The
    exact value is the only thing that can be told apart from prose.
    """
    cleaned = _TOKEN_PARAM.sub("…", message)
    if secret:
        cleaned = cleaned.replace(secret, "…")
    return cleaned


class EventLog:
    """A bounded log of what the agent has been doing lately."""

    def __init__(self, capacity: int = DEFAULT_CAPACITY) -> None:
        self._entries: deque[dict] = deque(maxlen=capacity)
        self._lock = threading.Lock()
        self._secret: str | None = None

    def guard(self, secret: str) -> None:
        """Tell the log which value must never appear in it."""
        with self._lock:
            self._secret = secret

    def add(self, kind: str, message: str) -> None:
        with self._lock:
            entry = {"kind": kind, "message": _redact(message, self._secret),
                     "at": time.time()}
            self._entries.append(entry)

    def entries(self) -> list[dict]:
        with self._lock:
            return list(reversed(self._entries))

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


log = EventLog()
