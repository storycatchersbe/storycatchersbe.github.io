#!/usr/bin/env python3
"""Optimize static HTML for search engines and AI crawlers."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parents[1]
SITE = "https://storycatchers.be"

LEGACY_META_BLOCK = re.compile(
    r"<!-- GENERAL META -->[\s\S]*?"
    r'<meta name="twitter:image" content="[^"]*" />\n',
)

ESSENTIAL_META = """\
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
<meta http-equiv="X-UA-Compatible" content="IE=edge" />
<meta name="msapplication-TileColor" content="#da532c" />
<meta name="theme-color" content="#ffffff" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
"""

SEO_META_PROPS = ("og:url", "og:image")

CONTACT_ORG_FIELDS = {
    "address": {
        "@type": "PostalAddress",
        "streetAddress": "Komiteitstraat 46-52",
        "addressLocality": "Merksem",
        "postalCode": "2170",
        "addressRegion": "Antwerpen",
        "addressCountry": "BE",
    },
    "telephone": "+3233699446",
    "email": "hallo@storycatchers.be",
}


def page_base_url(html_path: Path) -> str:
    rel_dir = html_path.parent.relative_to(ROOT)
    if str(rel_dir) == ".":
        return f"{SITE}/"
    return f"{SITE}/{rel_dir.as_posix()}/"


def to_absolute(url: str, base: str) -> str:
    if not url or url.startswith(("http://", "https://", "//")):
        return url
    resolved = urljoin(base, url)
    if url.endswith("/") and not resolved.endswith("/"):
        resolved += "/"
    return resolved


def fix_seo_urls(content: str, base: str) -> str:
    def replace_link_href(match: re.Match[str]) -> str:
        tag = match.group(0)
        href_match = re.search(r'href=(["\'])([^"\']+)\1', tag)
        if not href_match:
            return tag
        absolute = to_absolute(href_match.group(2), base)
        return tag[: href_match.start(2)] + absolute + tag[href_match.end(2) :]

    content = re.sub(
        r'<link rel="canonical"[^>]*/?>',
        replace_link_href,
        content,
    )
    content = re.sub(
        r'<link rel="alternate" hreflang="[^"]+"[^>]*/?>',
        replace_link_href,
        content,
    )

    for prop in SEO_META_PROPS:
        content = re.sub(
            rf'(<meta property="{re.escape(prop)}" content=")([^"]*)(")',
            lambda m, p=prop: m.group(1) + to_absolute(m.group(2), base) + m.group(3),
            content,
        )

    content = re.sub(
        r'(<meta name="twitter:image" content=")([^"]*)(")',
        lambda m: m.group(1) + to_absolute(m.group(2), base) + m.group(3),
        content,
    )

    return content


def fix_json_ld_urls(content: str) -> str:
    match = re.search(
        r'(<script type="application/ld\+json">)(.*?)(</script>)',
        content,
        re.DOTALL,
    )
    if not match:
        return content

    try:
        data = json.loads(match.group(2))
    except json.JSONDecodeError:
        return content

    def fix_node(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if (
                    key in ("url", "contentUrl", "thumbnailUrl")
                    and isinstance(value, str)
                    and value.startswith("/")
                ):
                    node[key] = SITE + value
                else:
                    fix_node(value)
        elif isinstance(node, list):
            for item in node:
                fix_node(item)

    fix_node(data)
    updated_json = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return content[: match.start(2)] + updated_json + content[match.end(2) :]


def add_twitter_title(content: str) -> str:
    if 'name="twitter:title"' in content:
        return content
    return re.sub(
        r'(<meta property="og:title" content="([^"]*)" />)',
        r'\1\n\t<meta name="twitter:title" content="\2" />',
        content,
        count=1,
    )


def enhance_contact_organization(content: str, html_path: Path) -> str:
    contact_paths = {"nl/contact/index.html", "en/contact/index.html"}
    rel = html_path.relative_to(ROOT).as_posix()
    if rel not in contact_paths:
        return content

    match = re.search(
        r'(<script type="application/ld\+json">)(.*?)(</script>)',
        content,
        re.DOTALL,
    )
    if not match:
        return content

    try:
        data = json.loads(match.group(2))
    except json.JSONDecodeError:
        return content

    graph = data.get("@graph", [])
    for node in graph:
        if node.get("@type") == "Organization":
            for key, value in CONTACT_ORG_FIELDS.items():
                if key not in node:
                    node[key] = value

    updated_json = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return content[: match.start(2)] + updated_json + content[match.end(2) :]


def optimize_html(content: str, html_path: Path) -> str:
    base = page_base_url(html_path)
    content = LEGACY_META_BLOCK.sub(ESSENTIAL_META, content)
    content = fix_seo_urls(content, base)
    content = fix_json_ld_urls(content)
    content = add_twitter_title(content)
    content = enhance_contact_organization(content, html_path)
    return content


def main() -> None:
    changed = 0
    for path in sorted(ROOT.rglob("*.html")):
        original = path.read_text(encoding="utf-8")
        updated = optimize_html(original, path)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed += 1
            print(f"updated: {path.relative_to(ROOT)}")

    print(f"\nDone. Updated {changed} file(s).")


if __name__ == "__main__":
    main()
