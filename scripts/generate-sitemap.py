#!/usr/bin/env python3
"""Generate sitemap.xml for storycatchers.be from static HTML files."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring

ROOT = Path(__file__).resolve().parents[1]
SITE = "https://storycatchers.be"
SITEMAP_PATH = ROOT / "sitemap.xml"

NOINDEX_PATTERN = re.compile(
    r'<meta\s+name=[\'"]robots[\'"]\s+content=[\'"][^"\']*noindex',
    re.IGNORECASE,
)
DATE_MODIFIED_PATTERN = re.compile(r'"dateModified"\s*:\s*"([^"]+)"')
HREFLANG_PATTERN = re.compile(
    r'<link\s+rel="alternate"\s+hreflang="([^"]+)"\s+href="([^"]+)"\s*/?>',
    re.IGNORECASE,
)
REDIRECT_PATTERN = re.compile(
    r'<meta\s+http-equiv=["\']refresh["\']',
    re.IGNORECASE,
)
CANONICAL_PATTERN = re.compile(
    r'<link\s+rel=["\']canonical["\']\s+href=["\']([^"\']+)["\']',
    re.IGNORECASE,
)


def page_url(html_path: Path) -> str | None:
    rel = html_path.relative_to(ROOT)
    parts = rel.parts

    if parts == ("index.html",):
        return f"{SITE}/nl/"

    if parts[0] in {"assets", "scripts", ".github", ".cursor"}:
        return None

    if parts[-1] != "index.html":
        return None

    if parts[0] == "404.html" or "404.html" in parts:
        return None

    url_path = "/" + "/".join(parts[:-1])
    if not url_path.endswith("/"):
        url_path += "/"
    return f"{SITE}{url_path}"


def extract_lastmod(content: str) -> str | None:
    match = DATE_MODIFIED_PATTERN.search(content)
    if not match:
        return None
    try:
        dt = datetime.fromisoformat(match.group(1).replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%d")
    except ValueError:
        return None


def normalize_loc(url: str) -> str:
    return url if url.endswith("/") else f"{url}/"


def is_redirect_stub(content: str, loc: str) -> bool:
    if REDIRECT_PATTERN.search(content):
        return True
    canonical_match = CANONICAL_PATTERN.search(content)
    if not canonical_match:
        return False
    return normalize_loc(canonical_match.group(1)) != normalize_loc(loc)


def extract_hreflang(content: str, page_url_value: str) -> list[tuple[str, str]]:
    alternates: list[tuple[str, str]] = []
    for hreflang, href in HREFLANG_PATTERN.findall(content):
        if href.startswith("http"):
            alternates.append((hreflang, href))
            continue
        # Skip unresolved relative hrefs — should be absolute after optimize script
        if href.startswith("../") or href.startswith("./"):
            continue
        alternates.append((hreflang, href if href.startswith("http") else f"{SITE}{href}"))
    return alternates


def build_sitemap(entries: list[dict]) -> str:
    urlset = Element(
        "urlset",
        xmlns="http://www.sitemaps.org/schemas/sitemap/0.9",
    )
    urlset.set("xmlns:xhtml", "http://www.w3.org/1999/xhtml")

    for entry in sorted(entries, key=lambda item: item["loc"]):
        url_el = SubElement(urlset, "url")
        SubElement(url_el, "loc").text = entry["loc"]
        if entry.get("lastmod"):
            SubElement(url_el, "lastmod").text = entry["lastmod"]
        for hreflang, href in entry.get("alternates", []):
            link_el = SubElement(
                url_el,
                "{http://www.w3.org/1999/xhtml}link",
            )
            link_el.set("rel", "alternate")
            link_el.set("hreflang", hreflang)
            link_el.set("href", href)

    xml_bytes = tostring(urlset, encoding="utf-8", xml_declaration=True)
    return xml_bytes.decode("utf-8")


def main() -> None:
    entries: list[dict] = []
    seen: set[str] = set()

    for html_path in sorted(ROOT.rglob("index.html")):
        rel = html_path.relative_to(ROOT).as_posix()
        if rel == "index.html":
            continue

        content = html_path.read_text(encoding="utf-8")
        if NOINDEX_PATTERN.search(content):
            continue

        loc = page_url(html_path)
        if not loc or loc in seen:
            continue
        if is_redirect_stub(content, loc):
            continue
        seen.add(loc)

        entries.append(
            {
                "loc": loc,
                "lastmod": extract_lastmod(content),
                "alternates": extract_hreflang(content, loc),
            }
        )

    sitemap_xml = build_sitemap(entries)
    SITEMAP_PATH.write_text(sitemap_xml, encoding="utf-8")
    print(f"Generated {SITEMAP_PATH.relative_to(ROOT)} with {len(entries)} URL(s).")


if __name__ == "__main__":
    main()
