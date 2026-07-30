#!/usr/bin/env python3
"""Optimize static HTML for search engines and AI crawlers."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parents[1]
SITE = "https://storycatchers.be"
DESCRIPTIONS_PATH = Path(__file__).with_name("seo-descriptions.json")
JOB_POSTINGS_PATH = Path(__file__).with_name("job-postings.json")

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

EN_WEBSITE_DESCRIPTION = (
    "Digital studio productions and webinars for ambitious organizations."
)
CAREERS_URL = f"{SITE}/nl/werken-bij-storycatchers/"
CAREERS_BREADCRUMB_NAME = "Werken bij Storycatchers"
JOB_LOCATION = {
    "@type": "Place",
    "address": CONTACT_ORG_FIELDS["address"],
}
ORGANIZATION_LOGO = (
    f"{SITE}/assets/images/uploads/2023/01/Storycatchers-Logo.png"
)

TITLE_SUFFIX = " | Storycatchers"

TITLE_OVERRIDES: dict[str, str] = {
    "index.html": "Digitale studioproducties voor ambitieuze organisaties",
}


def load_descriptions() -> dict[str, str]:
    if not DESCRIPTIONS_PATH.exists():
        return {}
    return json.loads(DESCRIPTIONS_PATH.read_text(encoding="utf-8"))


def load_job_postings() -> dict[str, dict[str, str]]:
    if not JOB_POSTINGS_PATH.exists():
        return {}
    return json.loads(JOB_POSTINGS_PATH.read_text(encoding="utf-8"))


def extract_meta_content(content: str, *, name: str | None = None, prop: str | None = None) -> str | None:
    if name:
        match = re.search(
            rf'<meta name="{re.escape(name)}" content="([^"]*)"',
            content,
        )
    elif prop:
        match = re.search(
            rf'<meta property="{re.escape(prop)}" content="([^"]*)"',
            content,
        )
    else:
        return None
    return html.unescape(match.group(1)).strip() if match else None


def extract_title_tag(content: str) -> str | None:
    match = re.search(r"<title>\s*(.*?)\s*</title>", content, re.DOTALL)
    if not match:
        return None
    return re.sub(r"\s+", " ", match.group(1)).strip()


def normalize_page_title(raw: str) -> str:
    cleaned = re.sub(r"\s+", " ", raw).strip()
    for prefix in ("Storycatchers - ", "Storycatchers – "):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix) :].strip()
    for suffix in (" - Storycatchers", " – Storycatchers", TITLE_SUFFIX):
        if cleaned.endswith(suffix):
            cleaned = cleaned[: -len(suffix)].strip()
    if not cleaned or cleaned == "Storycatchers":
        return ""
    return cleaned


def resolve_title(content: str, html_path: Path) -> str:
    rel = html_path.relative_to(ROOT).as_posix()
    if rel in TITLE_OVERRIDES:
        return f"{TITLE_OVERRIDES[rel]}{TITLE_SUFFIX}"

    for source in (
        extract_meta_content(content, prop="og:title"),
        extract_title_tag(content),
    ):
        if not source:
            continue
        page_title = normalize_page_title(source)
        if page_title:
            return f"{page_title}{TITLE_SUFFIX}"

    fallback = extract_title_tag(content) or "Storycatchers"
    page_title = normalize_page_title(fallback)
    return f"{page_title}{TITLE_SUFFIX}" if page_title else fallback


def set_title_tag(content: str, title: str) -> str:
    return re.sub(
        r"<title>\s*.*?\s*</title>",
        f"    <title>{html.escape(title)}</title>",
        content,
        count=1,
        flags=re.DOTALL,
    )


def set_meta_content(
    content: str,
    value: str,
    *,
    name: str | None = None,
    prop: str | None = None,
) -> str:
    escaped = html.escape(value, quote=True)
    if name:
        pattern = rf'(<meta name="{re.escape(name)}" content=")[^"]*(")'
    elif prop:
        pattern = rf'(<meta property="{re.escape(prop)}" content=")[^"]*(")'
    else:
        return content

    if re.search(pattern, content):
        return re.sub(pattern, rf"\1{escaped}\2", content, count=1)

    if name == "description":
        insertion = f'\t<meta name="description" content="{escaped}" />\n'
        canonical = re.search(r"(\t<link rel=\"canonical\")", content)
        if canonical:
            return content[: canonical.start()] + insertion + content[canonical.start() :]
        robots = re.search(r"(<meta name='robots'[^>]*/>\n)", content)
        if robots:
            return content[: robots.end()] + insertion + content[robots.end() :]
    elif prop == "og:description":
        insertion = f'\t<meta property="og:description" content="{escaped}" />\n'
        og_title = re.search(r'(<meta property="og:title"[^>]*/>\n)', content)
        if og_title:
            return content[: og_title.end()] + insertion + content[og_title.end() :]
    elif name == "twitter:description":
        insertion = f'\t<meta name="twitter:description" content="{escaped}" />\n'
        twitter_title = re.search(r'(<meta name="twitter:title"[^>]*/>\n)', content)
        if twitter_title:
            return content[: twitter_title.end()] + insertion + content[twitter_title.end() :]
        twitter_card = re.search(r'(<meta name="twitter:card"[^>]*/>\n)', content)
        if twitter_card:
            return content[: twitter_card.end()] + insertion + content[twitter_card.end() :]

    return content


def sync_twitter_from_og(content: str) -> str:
    og_title = extract_meta_content(content, prop="og:title")
    og_description = extract_meta_content(content, prop="og:description")
    og_image = extract_meta_content(content, prop="og:image")

    if og_title:
        content = set_meta_content(content, og_title, name="twitter:title")
        if 'name="twitter:title"' not in content:
            content = re.sub(
                r'(<meta property="og:title" content="[^"]*" />)',
                rf'\1\n\t<meta name="twitter:title" content="{html.escape(og_title, quote=True)}" />',
                content,
                count=1,
            )

    meta_description = extract_meta_content(content, name="description")
    twitter_description = meta_description or og_description
    if twitter_description:
        content = set_meta_content(content, twitter_description, name="twitter:description")
        if 'name="twitter:description"' not in content:
            source = meta_description or og_description
            if source:
                content = re.sub(
                    r'(<meta property="og:description" content="[^"]*" />)',
                    rf'\1\n\t<meta name="twitter:description" content="{html.escape(source, quote=True)}" />',
                    content,
                    count=1,
                )

    if og_image and 'name="twitter:image"' not in content:
        content = re.sub(
            r'(<meta name="twitter:card"[^>]*/>)',
            rf'\1\n\t<meta name="twitter:image" content="{html.escape(og_image, quote=True)}" />',
            content,
            count=1,
        )

    return content


def normalize_titles(content: str, html_path: Path) -> str:
    title = resolve_title(content, html_path)
    content = set_title_tag(content, title)
    content = set_meta_content(content, title, prop="og:title")
    content = set_meta_content(content, title, name="twitter:title")
    if 'property="og:title"' not in content:
        canonical = re.search(r'(<link rel="canonical"[^>]*/>\n)', content)
        if canonical:
            tag = f'\t<meta property="og:title" content="{html.escape(title, quote=True)}" />\n'
            content = content[: canonical.end()] + tag + content[canonical.end() :]
    if 'name="twitter:title"' not in content and 'property="og:title"' in content:
        content = sync_twitter_from_og(content)
    return content


def apply_description(content: str, html_path: Path, descriptions: dict[str, str]) -> str:
    rel = html_path.relative_to(ROOT).as_posix()
    description = descriptions.get(rel)
    if not description:
        return content

    content = set_meta_content(content, description, name="description")
    content = set_meta_content(content, description, prop="og:description")
    content = set_meta_content(content, description, name="twitter:description")
    return content


def update_json_ld_metadata(content: str, title: str, description: str | None) -> str:
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

    for node in data.get("@graph", []):
        if node.get("@type") == "WebPage":
            node["name"] = title
            if description:
                node["description"] = description

    updated_json = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return content[: match.start(2)] + updated_json + content[match.end(2) :]


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


def is_english_page(html_path: Path, content: str) -> bool:
    rel = html_path.relative_to(ROOT).as_posix()
    if rel.startswith("en/"):
        return True
    return bool(re.search(r'<html[^>]*\slang=["\']en["\']', content, re.IGNORECASE))


def replace_json_ld_refs(node: object, replacements: dict[str, str]) -> None:
    if isinstance(node, dict):
        for key, value in list(node.items()):
            if isinstance(value, str) and value in replacements:
                node[key] = replacements[value]
            else:
                replace_json_ld_refs(value, replacements)
    elif isinstance(node, list):
        for item in node:
            replace_json_ld_refs(item, replacements)


def fix_vacancy_breadcrumbs(graph: list[dict]) -> None:
    for node in graph:
        if node.get("@type") != "BreadcrumbList":
            continue
        for item in node.get("itemListElement", []):
            if item.get("item") == f"{SITE}/nl/vacatures/":
                item["item"] = CAREERS_URL
                item["name"] = CAREERS_BREADCRUMB_NAME


def localize_english_json_ld(graph: list[dict]) -> None:
    replacements = {
        f"{SITE}/nl/#website": f"{SITE}/en/#website",
        f"{SITE}/nl/#organization": f"{SITE}/en/#organization",
    }
    replace_json_ld_refs(graph, replacements)

    for node in graph:
        node_type = node.get("@type")
        if node_type == "WebSite":
            node["@id"] = f"{SITE}/en/#website"
            node["url"] = f"{SITE}/en/"
            node["description"] = EN_WEBSITE_DESCRIPTION
            node["inLanguage"] = "en-US"
            if isinstance(node.get("publisher"), dict):
                node["publisher"]["@id"] = f"{SITE}/en/#organization"
        elif node_type == "Organization":
            node["@id"] = f"{SITE}/en/#organization"
            node["url"] = f"{SITE}/en/"


def build_job_posting(page_url: str, job: dict[str, str], description: str | None) -> dict:
    job_id = f"{page_url}#jobposting"
    return {
        "@type": "JobPosting",
        "@id": job_id,
        "title": job["title"],
        "description": description or job["title"],
        "datePosted": job["datePosted"],
        "validThrough": job.get("validThrough"),
        "employmentType": job["employmentType"],
        "hiringOrganization": {
            "@type": "Organization",
            "name": "Storycatchers",
            "sameAs": f"{SITE}/nl/",
            "logo": ORGANIZATION_LOGO,
        },
        "jobLocation": JOB_LOCATION,
        "applicantLocationRequirements": {
            "@type": "Country",
            "name": "BE",
        },
        "directApply": True,
        "applicationContact": {
            "@type": "ContactPoint",
            "email": job["applicationContact"],
            "contactType": "recruiting",
        },
        "identifier": {
            "@type": "PropertyValue",
            "name": "Storycatchers",
            "value": job["identifier"],
        },
        "mainEntityOfPage": {"@id": page_url},
    }


def enhance_json_ld(
    content: str,
    html_path: Path,
    job_postings: dict[str, dict[str, str]],
) -> str:
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
    if not graph:
        return content

    fix_vacancy_breadcrumbs(graph)
    if is_english_page(html_path, content):
        localize_english_json_ld(graph)

    rel = html_path.relative_to(ROOT).as_posix()
    job = job_postings.get(rel)
    if job:
        page_url = page_base_url(html_path).rstrip("/") + "/"
        description = extract_meta_content(content, name="description")
        graph[:] = [node for node in graph if node.get("@type") != "JobPosting"]
        job_posting = build_job_posting(page_url, job, description)
        graph.append(job_posting)
        for node in graph:
            if node.get("@type") == "WebPage":
                node["mainEntity"] = {"@id": job_posting["@id"]}

    updated_json = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return content[: match.start(2)] + updated_json + content[match.end(2) :]


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


def optimize_html(
    content: str,
    html_path: Path,
    descriptions: dict[str, str],
    job_postings: dict[str, dict[str, str]],
) -> str:
    base = page_base_url(html_path)
    content = LEGACY_META_BLOCK.sub(ESSENTIAL_META, content)
    content = fix_seo_urls(content, base)
    content = fix_json_ld_urls(content)
    content = normalize_titles(content, html_path)
    content = apply_description(content, html_path, descriptions)
    content = sync_twitter_from_og(content)

    title = resolve_title(content, html_path)
    description = extract_meta_content(content, name="description")
    content = update_json_ld_metadata(content, title, description)

    content = enhance_json_ld(content, html_path, job_postings)
    content = enhance_contact_organization(content, html_path)
    return content


def main() -> None:
    descriptions = load_descriptions()
    job_postings = load_job_postings()
    changed = 0
    for path in sorted(ROOT.rglob("*.html")):
        original = path.read_text(encoding="utf-8")
        updated = optimize_html(original, path, descriptions, job_postings)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed += 1
            print(f"updated: {path.relative_to(ROOT)}")

    print(f"\nDone. Updated {changed} file(s).")


if __name__ == "__main__":
    main()
