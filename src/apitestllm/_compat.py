"""API TEST CLI - Shared runtime compatibility helpers."""

import sys
from typing import Any, cast


def ensure_utf8_stdio() -> None:
    """Force UTF-8 on stdout/stderr where the stream supports it.

    Uses ``getattr`` instead of direct attribute access so static type
    checkers (basedpyright: ``sys.stdout`` is ``TextIO``) stay clean while
    legacy Windows consoles still get ``reconfigure(encoding="utf-8")``.
    Never raises.
    """
    for stream_name in ("stdout", "stderr"):
        stream = cast(Any, getattr(sys, stream_name, None))
        if stream is None:
            continue
        reconfigure = getattr(stream, "reconfigure", None)
        if not callable(reconfigure):
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            continue
