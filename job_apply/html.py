from __future__ import annotations

import html
import re

_TAG = re.compile(r"<[^>]+>", re.I)
_SPACE = re.compile(r"\s+")


def strip_html(value: str | None) -> str:
    if not value:
        return ""
    text = html.unescape(_TAG.sub(" ", value))
    return _SPACE.sub(" ", text).strip()
