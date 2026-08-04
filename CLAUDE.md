# Storycatchers website

Static, no-build marketing site for [Storycatchers](https://storycatchers.be) (video/webinar/event productions, Antwerp). Plain HTML/CSS/JS — no bundler, no framework, no `package.json`. Content was originally migrated off WordPress; some tooling still reflects that (see `scripts/cleanup-wordpress-references.py`).

## Structure

- `nl/` — Dutch pages (primary language), `en/` — English pages. Every NL page has a mirrored EN counterpart at an analogous (translated) path, e.g. `nl/aanbod/webinars/` ↔ `en/services/webinars/`.
- `index.html` at the root just redirects to `nl/`.
- `assets/` — css, js, fonts, images, video. No build step: edit these files directly.
- `nl/productie/` — internal production docs, deliberately excluded from indexing (`robots.txt` disallow, not linked in `llms.txt`). Don't link to it from public pages.
- `scripts/` — Python maintenance scripts, run manually and locally (no CI hook committed here):
  - `optimize-seo-for-ai.py` — the SEO/AEO pipeline. Normalizes `<title>`, meta description, OG/Twitter tags, canonical/hreflang URLs, and JSON-LD (`WebPage`, `Organization`, `BreadcrumbList`, `JobPosting`, etc.) across every `*.html` file. Descriptions come from `seo-descriptions.json` (keyed by page path); job postings from `job-postings.json`. **Run this after adding or editing any page** so meta/structured data stay consistent — it's idempotent.
  - `generate-sitemap.py` — regenerates `sitemap.xml` from the HTML tree (skips `noindex` and redirect pages, follows hreflang links). Run after adding/removing pages.
  - `generate-video-posters.py`, `cleanup-wordpress-references.py` — one-off/occasional maintenance, not part of the regular edit loop.

## Local preview

```bash
./serve.command
```
or `python3 -m http.server 8811`, then open `http://localhost:8811/nl/`.

## AI/SEO discoverability

`robots.txt` allows all crawlers (wildcard `Allow: /`, so this already covers ClaudeBot/GPTBot/etc.) except `/nl/productie/`. `llms.txt` is a hand-curated index of key pages for LLM answer engines — update it when major sections are added/renamed, but it isn't meant to be exhaustive (`sitemap.xml` is exhaustive; `generate-sitemap.py` regenerates it). Every page carries `Organization`/`LocalBusiness` JSON-LD with address/contact info (not just `/contact/`), so keep `CONTACT_ORG_FIELDS` in `optimize-seo-for-ai.py` as the single source of truth for that data rather than hand-editing JSON-LD in individual pages.

## Editing pages

Pages are hand-authored HTML, not templated — when changing shared chrome (nav, footer, cookie banner) you generally need to repeat the edit across every page, in both `nl/` and `en/`. After content edits: re-run `optimize-seo-for-ai.py`, and `generate-sitemap.py` if pages were added/removed/renamed.

## Git & deploy

Remote: `https://github.com/storycatchersbe/storycatchersbe.github.io.git`. Work on a feature branch, push, PR into `main`. Merging to `main` deploys automatically to GitHub Pages (custom domain via `CNAME`). See [README.md](README.md) for the full workflow.
