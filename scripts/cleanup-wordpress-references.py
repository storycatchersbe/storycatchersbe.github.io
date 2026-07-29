#!/usr/bin/env python3
"""Remove leftover WordPress / Yoast / Complianz plugin references from static HTML."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"<!-- SEE YOAST -->\n?", re.IGNORECASE), ""),
    (
        re.compile(
            r"\t<!-- This site is optimized with the Yoast SEO plugin.*?-->\n",
            re.IGNORECASE | re.DOTALL,
        ),
        "",
    ),
    (re.compile(r"\t<!-- / Yoast SEO plugin\. -->\n?", re.IGNORECASE), ""),
    (re.compile(r' class="yoast-schema-graph"'), ""),
    (
        re.compile(
            r"<!-- Consent Management powered by Complianz.*?-->\n?",
            re.IGNORECASE | re.DOTALL,
        ),
        "",
    ),
    (re.compile(r"//# sourceURL=cmplz-cookiebanner-js-extra\n?", re.IGNORECASE), ""),
    (
        re.compile(r"<!-- Statistics script Complianz GDPR/CCPA -->\n?", re.IGNORECASE),
        "",
    ),
    (
        re.compile(r'"url":"[^"]*wp-json/complianz/v1/"'),
        '"url":""',
    ),
    (
        re.compile(
            r',?"potentialAction":\[\{"@type":"SearchAction".*?search_term_string.*?\}\]',
            re.DOTALL,
        ),
        "",
    ),
]


def clean_html(content: str) -> str:
    for pattern, replacement in PATTERNS:
        content = pattern.sub(replacement, content)
    return content


def main() -> None:
    changed_files = 0

    for path in sorted(ROOT.rglob("*.html")):
        original = path.read_text(encoding="utf-8")
        cleaned = clean_html(original)
        if cleaned != original:
            path.write_text(cleaned, encoding="utf-8")
            changed_files += 1
            print(f"updated: {path.relative_to(ROOT)}")

    print(f"\nDone. Updated {changed_files} file(s).")


if __name__ == "__main__":
    main()
