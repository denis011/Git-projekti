#!/usr/bin/env python3
"""CLI helper for listing new Veseli Cetvrtak comic releases by series."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import unicodedata
import warnings
import urllib.request
import urllib.error
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

warnings.filterwarnings(
    "ignore",
    message="Bad certificate in Windows certificate store",
    category=UserWarning,
    module="ssl",
)

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except (AttributeError, ValueError):
        pass


DEFAULT_FEED_CANDIDATES: Tuple[str, ...] = (
    "https://veselicetvrtak.com/izdanja/feed/",
    "https://veselicetvrtak.com/feed/?post_type=product",
    "https://veselicetvrtak.com/?post_type=product&feed=rss2",
)
DEFAULT_FEED_URL = DEFAULT_FEED_CANDIDATES[0]
DEFAULT_TIMEOUT = 15

# Map display name -> tuple of match keywords (normalized to ASCII, lowercase)
DEFAULT_SERIES: Dict[str, Tuple[str, ...]] = {
    "Dylan Dog": ("dylan dog", "dilan dog"),
    "Martin Mystere": ("martin mystere", "marti misterija"),
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


def fetch_feed(
    url: str,
    timeout: int = DEFAULT_TIMEOUT,
    fallbacks: Sequence[str] = (),
) -> bytes:
    errors: List[str] = []
    for candidate in (url, *fallbacks):
        request = urllib.request.Request(
            candidate,
            headers={
                "User-Agent": "veseli-cetvrtak-new-releases/1.0 (+https://github.com/)",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as err:
            errors.append(
                f"{candidate} -> HTTP {err.code} {err.reason or ''}".rstrip()
            )
        except Exception as exc:
            errors.append(f"{candidate} -> {exc}")
    raise RuntimeError("All feed URLs failed:\n" + "\n".join(errors))


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
            return Release(
                series=series_name,
                title=title_elem.strip(),
                link=link_elem.strip(),
                published=published,
            )
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
        date_part = release.published.strftime("%Y/%m/%d") if release.published else "Unknown date"
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


def _with_paged(url: str, paged: int) -> str:
    if paged <= 1:
        return url
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["paged"] = str(paged)
    new_query = urlencode(query, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def write_releases_csv(path: str, releases: Sequence[Release]) -> None:
    """Append releases to CSV with a fetched timestamp, skipping duplicates."""
    dir_name = os.path.dirname(os.path.abspath(path))
    if dir_name and not os.path.exists(dir_name):
        os.makedirs(dir_name, exist_ok=True)

    existing_keys = set()
    if os.path.exists(path) and os.path.getsize(path) > 0:
        with open(path, "r", encoding="utf-8", newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                existing_keys.add(
                    (
                        row.get("series", ""),
                        row.get("title", ""),
                        row.get("link", ""),
                    )
                )

    run_timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    fieldnames = ("fetched_at", "series", "title", "link", "published")
    new_rows = []
    for release in releases:
        key = (release.series, release.title, release.link)
        if key in existing_keys:
            continue
        existing_keys.add(key)
        new_rows.append(
            {
                "fetched_at": run_timestamp,
                "series": release.series,
                "title": release.title,
                "link": release.link,
                "published": release.published.isoformat() if release.published else "",
            }
        )

    if not new_rows:
        return

    file_exists = os.path.exists(path)
    with open(path, "a", encoding="utf-8", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists or os.path.getsize(path) == 0:
            writer.writeheader()
        writer.writerows(new_rows)


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
        description="Fetch and filter Veseli Cetvrtak product feed for new releases by series.",
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
    parser.add_argument(
        "--paged",
        type=int,
        default=1,
        help="Number of feed pages to fetch starting from page 1 (default: %(default)s).",
    )
    parser.add_argument(
        "--csv",
        help="Append results to the given CSV file for historical tracking.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    series_matchers = build_series_matchers(args.series)
    page_count = max(args.paged, 1)
    all_releases: List[Release] = []
    seen_keys = set()

    for page in range(1, page_count + 1):
        try:
            fallbacks: Sequence[str] = ()
            if args.feed_url == DEFAULT_FEED_URL:
                fallbacks = tuple(_with_paged(url, page) for url in DEFAULT_FEED_CANDIDATES[1:])
            feed_url = _with_paged(args.feed_url, page)
            feed_xml = fetch_feed(feed_url, fallbacks=fallbacks)
        except Exception as exc:  # pragma: no cover - network failures aren't predictable
            print(f"Failed to download feed page {page}: {exc}", file=sys.stderr)
            if page == 1:
                return 1
            continue

        page_releases = load_releases(feed_xml, series_matchers)
        for release in page_releases:
            key = (release.series, release.title, release.link)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            all_releases.append(release)

    if not all_releases:
        return 0

    all_releases.sort(key=lambda rel: rel.published or datetime.min, reverse=True)
    releases = all_releases
    if args.limit is not None:
        releases = releases[: max(args.limit, 0)]

    if args.csv:
        write_releases_csv(args.csv, releases)

    if args.json:
        print(releases_to_json(releases))
    else:
        print(format_releases_text(releases))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
