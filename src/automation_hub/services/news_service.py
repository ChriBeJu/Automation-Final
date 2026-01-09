from __future__ import annotations

import html
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime

from automation_hub.logging_utils import get_logger


@dataclass(frozen=True)
class NewsFeed:
    name: str
    url: str


@dataclass(frozen=True)
class NewsItem:
    source: str
    title: str
    summary: str
    fetched_at: datetime


class NewsService:
    def __init__(self, feeds: list[NewsFeed], timeout_sec: int, max_items: int) -> None:
        self.feeds = feeds
        self.timeout_sec = timeout_sec
        self.max_items = max_items
        self.logger = get_logger("automation_hub.news")

    def fetch_items(self) -> list[NewsItem]:
        items: list[NewsItem] = []
        if not self.feeds:
            return items
        for feed in self.feeds:
            try:
                items.extend(self._fetch_feed(feed))
            except Exception as exc:  # noqa: BLE001
                self.logger.warning("Failed to fetch %s: %s", feed.url, exc)
            if len(items) >= self.max_items:
                break
        return items[: self.max_items]

    def _fetch_feed(self, feed: NewsFeed) -> list[NewsItem]:
        request = urllib.request.Request(
            feed.url, headers={"User-Agent": "automation-hub/1.0"}
        )
        with urllib.request.urlopen(request, timeout=self.timeout_sec) as response:
            raw = response.read()
        root = ET.fromstring(raw)
        fetched_at = datetime.utcnow()
        items = []
        entries = root.findall(".//{*}item") or root.findall(".//{*}entry")
        for entry in entries:
            title = _clean_text(_find_text(entry, ["title"]))
            if not title:
                continue
            summary = _clean_text(
                _find_text(entry, ["description", "summary", "content"])
            )
            items.append(
                NewsItem(
                    source=feed.name,
                    title=title,
                    summary=summary,
                    fetched_at=fetched_at,
                )
            )
            if len(items) >= self.max_items:
                break
        return items


def _find_text(node: ET.Element, tags: list[str]) -> str:
    for tag in tags:
        child = node.find(f".//{{*}}{tag}")
        if child is not None and child.text:
            return child.text
    return ""


def _clean_text(value: str) -> str:
    if not value:
        return ""
    decoded = html.unescape(value)
    compact = " ".join(decoded.replace("\n", " ").replace("\r", " ").split())
    return compact.strip()
