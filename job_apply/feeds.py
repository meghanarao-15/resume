from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import urlparse

from .html import strip_html
from .http import get_text
from .models import Job


def assert_http_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeError("Feed URL must be http(s)")
    return url


def parse_job_feed(text: str, *, source: str) -> list[Job]:
    raw = (text or "").strip()
    if not raw:
        return []
    if raw[0] in "[{":
        return _from_json(json.loads(raw), source)
    return _from_xml(raw, source)


def fetch_job_feed(url: str, *, source: str, user_agent: str) -> list[Job]:
    body = get_text(assert_http_url(url), user_agent=user_agent)
    return parse_job_feed(body, source=source)


def _from_json(payload: Any, source: str) -> list[Job]:
    items: list[Any]
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        items = payload.get("jobs") or payload.get("items") or payload.get("results") or []
    else:
        return []
    jobs: list[Job] = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        title = item.get("title") or item.get("text") or ""
        url = item.get("url") or item.get("link") or ""
        if not title or not url:
            continue
        jobs.append(
            Job(
                id=f"{source}-feed:{item.get('id') or i}",
                source=f"{source}-feed",
                title=str(title),
                company=str(item.get("company") or item.get("company_name") or source),
                url=str(url),
                location=str(item.get("location") or ""),
                description=strip_html(str(item.get("description") or ""))[:4000],
                extra={"fetch_mode": "live-feed"},
            )
        )
    return jobs


def _local(tag: str) -> str:
    return tag.split("}", 1)[-1]


def _child_text(node: ET.Element, names: tuple[str, ...]) -> str:
    for child in list(node):
        if _local(child.tag) in names:
            if child.text and child.text.strip():
                return child.text.strip()
            href = child.attrib.get("href")
            if href:
                return href
    return ""


def _from_xml(raw: str, source: str) -> list[Job]:
    root = ET.fromstring(raw)
    nodes: list[ET.Element] = []
    for node in root.iter():
        if _local(node.tag) in {"item", "entry"}:
            nodes.append(node)
    jobs: list[Job] = []
    for i, node in enumerate(nodes):
        title = _child_text(node, ("title",))
        url = _child_text(node, ("link", "id"))
        if not url:
            url = node.findtext("link") or ""
        desc = _child_text(node, ("description", "summary", "content"))
        company = _child_text(node, ("author", "source", "name")) or source
        if not title or not url:
            continue
        jobs.append(
            Job(
                id=f"{source}-feed:{i}:{url}",
                source=f"{source}-feed",
                title=title,
                company=company,
                url=url,
                location="",
                description=strip_html(desc)[:4000],
                extra={"fetch_mode": "live-feed"},
            )
        )
    return jobs
