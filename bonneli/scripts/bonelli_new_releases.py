#!/usr/bin/env python3
"""CLI helper for listing new Sergio Bonelli comic releases by series."""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


DEFAULT_FEED_URL = "https://en.shop.sergiobonelli.it/rss/ultime-uscite"
DEFAULT_TIMEOUT = 15

# Map display name -> tuple of match keywords (normalized to ASCII, lowercase)
DEFAULT_SERIES: Dict[str, Tuple[str, ...]] = {
    "Dylan Dog": ("dylan dog",),
    "Martin Mystere": ("martin mystere", "martin mystère", "marti misterija"),
    "Zagor": ("zagor",),
}


@dataclass
class Release:
    series: str
    title: str
    link: str
    published: Optional[datetime]


def _normalize(text: str) -> str:
    """Lowercase ASCII approximation for consistent string matching."""
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()


def fetch_feed(url: str, timeout: int = DEFAULT_TIMEOUT) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "bonelli-new-releases/1.0 (+https://github.com/)"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def parse_feed(feed_xml: bytes) -> Iterable[ET.Element]:
    root = ET.fromstring(feed_xml)
    channel = root.find("channel")
    if channel is None:
        return []
    return channel.findall("item")


def extract_release(
    item: ET.Element,
    series_matchers: Dict[str, Tuple[str, ...]],
) -> Optional[Release]:
    title_elem = item.findtext("title") or ""
    link_elem = item.findtext("link") or ""
    pub_date_raw = item.findtext("pubDate")
    published = None
    if pub_date_raw:
        try:
            published = parsedate_to_datetime(pub_date_raw)
        except (TypeError, ValueError):
            published = None

    normalized_title = _normalize(title_elem)
    for series_name, keywords in series_matchers.items():
        if any(keyword in normalized_title for keyword in keywords):
            return Release(series=series_name, title=title_elem.strip(), link=link_elem.strip(), published=published)
    return None


def load_releases(feed_xml: bytes, series_matchers: Dict[str, Tuple[str, ...]]) -> List[Release]:
    releases: List[Release] = []
    for item in parse_feed(feed_xml):
        release = extract_release(item, series_matchers)
        if release:
            releases.append(release)
    releases.sort(key=lambda rel: rel.published or datetime.min, reverse=True)
    return releases


def format_releases_text(releases: Sequence[Release]) -> str:
    lines = []
    for release in releases:
        date_part = release.published.strftime("%Y-%m-%d") if release.published else "Unknown date"
        lines.append(f"{date_part} | {release.series} | {release.title} | {release.link}")
    return "\n".join(lines)


def releases_to_json(releases: Sequence[Release]) -> str:
    payload = [
        {
            "series": release.series,
            "title": release.title,
            "link": release.link,
            "published": release.published.isoformat() if release.published else None,
        }
        for release in releases
    ]
    return json.dumps(payload, indent=2, ensure_ascii=False)


def build_series_matchers(series_overrides: Optional[Sequence[str]]) -> Dict[str, Tuple[str, ...]]:
    if not series_overrides:
        return DEFAULT_SERIES
    matchers: Dict[str, Tuple[str, ...]] = {}
    for series in series_overrides:
        normalized = _normalize(series)
        matchers[series] = (normalized,)
    return matchers


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch and filter Sergio Bonelli 'New Releases' feed.",
    )
    parser.add_argument(
        "--feed-url",
        default=DEFAULT_FEED_URL,
        help="RSS feed URL to fetch (default: %(default)s).",
    )
    parser.add_argument(
        "--series",
        nargs="+",
        help="Override series names to match (default: Dylan Dog, Martin Mystere, Zagor).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit the number of releases shown.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    series_matchers = build_series_matchers(args.series)

    try:
        feed_xml = fetch_feed(args.feed_url)
    except Exception as exc:  # pragma: no cover - network failures aren't predictable
        print(f"Failed to download feed: {exc}", file=sys.stderr)
        return 1

    releases = load_releases(feed_xml, series_matchers)
    if args.limit is not None:
        releases = releases[: max(args.limit, 0)]

    if args.json:
        print(releases_to_json(releases))
    else:
        print(format_releases_text(releases))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
