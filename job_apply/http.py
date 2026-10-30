from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

DEFAULT_TIMEOUT = 25


def get_json(
    url: str,
    *,
    user_agent: str,
    headers: dict[str, str] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> Any:
    req_headers = {"User-Agent": user_agent, "Accept": "application/json"}
    if headers:
        req_headers.update(headers)
    request = urllib.request.Request(url, headers=req_headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} for {url}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error for {url}: {exc.reason}") from exc
    return json.loads(raw)


def get_text(
    url: str,
    *,
    user_agent: str,
    headers: dict[str, str] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    req_headers = {
        "User-Agent": user_agent,
        "Accept": "application/rss+xml, application/atom+xml, application/json, application/xml, text/xml, text/plain",
    }
    if headers:
        req_headers.update(headers)
    request = urllib.request.Request(url, headers=req_headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} for {url}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error for {url}: {exc.reason}") from exc


def env_ready(names: list[str]) -> bool:
    return all(os.environ.get(name) for name in names)
