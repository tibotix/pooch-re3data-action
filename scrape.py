#!/usr/bin/env python3
"""Scrape re3data repositories and emit repository URLs filtered by software."""

import argparse
from pathlib import Path
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

RE3DATA_LIST_URL = "https://re3data.org/api/beta/repositories"
REPOSITORY_DETAIL_FRAGMENT = "/api/beta/repository/"
HTTP_TIMEOUT_SECONDS = 30
USER_AGENT = "pooch-re3data-action/1.0"


def fetch_xml(url):
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/xml",
            "User-Agent": USER_AGENT,
        },
    )
    with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
        charset = response.headers.get_content_charset("utf-8")
        payload = response.read().decode(charset, errors="replace")
    try:
        return ET.fromstring(payload)
    except ET.ParseError as exc:
        raise RuntimeError(f"Invalid XML returned from {url}: {exc}") from exc


def local_name(tag):
    return tag.rsplit("}", 1)[-1]


def next_page_url(root):
    for elem in root.iter():
        tag = local_name(elem.tag)
        if (
            tag == "link"
            and (elem.attrib.get("rel") or "").strip().casefold() == "next"
        ):
            href = elem.attrib.get("href")
            if href:
                return href
        if tag == "next":
            href = elem.attrib.get("href")
            if href:
                return href
            text = (elem.text or "").strip()
            if text:
                return text

    return None


def collect_repository_detail_urls(software):
    start_url = (
        f"{RE3DATA_LIST_URL}?query=&software[]={urllib.parse.quote_plus(software)}"
    )
    detail_urls = set()
    visited_pages = set()
    page_url = start_url

    while page_url and page_url not in visited_pages:
        visited_pages.add(page_url)
        root = fetch_xml(page_url)
        for elem in root.iter():
            href = elem.attrib.get("href")
            if href and REPOSITORY_DETAIL_FRAGMENT in href:
                detail_urls.add(href)
        page_url = next_page_url(root)

    return sorted(detail_urls)


def extract_repository_urls(root):
    urls = set()
    for elem in root.iter():
        if local_name(elem.tag) != "repositoryURL":
            continue
        text = (elem.text or "").strip()
        if text:
            urls.add(text)
    return urls


def parse_blacklist_patterns(raw_value):
    patterns = []
    for line in raw_value.splitlines():
        for part in line.split(","):
            pattern = part.strip()
            if pattern:
                patterns.append(pattern)
    return patterns


def sanitize_repository_urls(urls: set[str]) -> set[str]:
    sanitized_urls = set()
    for url in urls:
        parsed = urllib.parse.urlsplit(url)._replace(query="", fragment="")
        if parsed.scheme == "http":
            parsed = parsed._replace(scheme="https")
        sanitized_urls.add(urllib.parse.urlunsplit(parsed))
    return sanitized_urls


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Fetch re3data repository records, filter by software, and write "
            "matching repository URLs to a file."
        )
    )
    parser.add_argument(
        "--software",
        required=True,
        help="Software value used in /repositories?query=&software[]=<value>.",
    )
    parser.add_argument(
        "--filename",
        required=True,
        help="Output file path. URLs are written one per line.",
    )
    parser.add_argument(
        "--blacklist",
        default="",
        help=(
            "Optional blacklist patterns (newline or comma separated). "
            "Any URL containing one of these patterns is excluded."
        ),
    )
    parser.add_argument(
        "--sanitize-urls",
        default=False,
        action="store_true",
        help=(
            "Strip query and fragment parts of repository URLs and rewrite http schemes to https."
        ),
    )
    args = parser.parse_args()

    try:
        detail_urls = collect_repository_detail_urls(args.software)
    except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
        print(f"Failed to retrieve re3data repository list: {exc}", file=sys.stderr)
        return 1

    repository_urls = set()
    processed = 0
    for detail_url in detail_urls:
        try:
            record_root = fetch_xml(detail_url)
        except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
            print(f"Skipping unreadable record {detail_url}: {exc}", file=sys.stderr)
            continue

        processed += 1
        repository_urls.update(extract_repository_urls(record_root))

    if args.sanitize_urls:
        repository_urls = sanitize_repository_urls(repository_urls)

    blacklist_patterns = parse_blacklist_patterns(args.blacklist)
    filtered_urls = [
        url
        for url in repository_urls
        if not any(pattern in url for pattern in blacklist_patterns)
    ]
    sorted_urls = sorted(filtered_urls)
    target = Path(args.filename)
    target.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(sorted_urls)
    if content:
        content += "\n"
    target.write_text(content, encoding="utf-8")

    print(
        f"Processed {processed} filtered repository records, "
        f"wrote {len(sorted_urls)} URLs to {args.filename} "
        f"(blacklist patterns: {len(blacklist_patterns)})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
