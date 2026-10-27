#!/usr/bin/env python3
"""Offline GitHub Pages validation: metadata, local links, IDs, assets and XML.

Runs without network access or dependencies. This validates structure, not
JavaScript behavior, actual deployments, accessibility compliance or Lighthouse.
"""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import json
import re
import sys
import xml.etree.ElementTree as ET
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
BASE_URL = "https://mskazemi.com/Vagrant-Kubernetes-ROS2-Deployment/"
ERRORS: list[str] = []


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.links: list[str] = []
        self.assets: list[str] = []
        self.canonical: str | None = None
        self.description: str | None = None
        self.title = False
        self.h1 = 0
        self.lang: str | None = None
        self.alt_missing = 0
        self.duplicates: list[str] = []
        self.jsonld: list[str] = []  # one entry per application/ld+json block
        self._inside_ld = False
        self.skip_link = False
        self.motion_toggle = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        ident = a.get("id")
        if ident:
            if ident in self.ids:
                self.duplicates.append(ident)
            self.ids.add(ident)
        if tag == "html":
            self.lang = a.get("lang")
        if tag == "h1":
            self.h1 += 1
        if tag == "title":
            self.title = True
        if tag == "meta" and a.get("name") == "description":
            self.description = a.get("content")
        if tag == "link" and a.get("rel") == "canonical":
            self.canonical = a.get("href")
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])
            if a["href"] == "#main":
                self.skip_link = True
        if "data-motion-toggle" in a:
            self.motion_toggle = True
        if a.get("aria-controls"):
            self.links.append("#" + a["aria-controls"])
        if tag in ("script", "link", "img", "source"):
            for attribute in ("src", "href"):
                value = a.get(attribute)
                if value and not re.match(r"^(https?:)?//", value) and not value.startswith(("data:", "#")):
                    self.assets.append(value)
        if tag == "img" and "alt" not in a:
            self.alt_missing += 1
        if tag == "script" and a.get("type") == "application/ld+json":
            self._inside_ld = True
            self.jsonld.append("")

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self._inside_ld = False

    def handle_data(self, data: str) -> None:
        if self._inside_ld:
            self.jsonld[-1] += data


def local_target(source: Path, reference: str) -> tuple[Path, str]:
    result = urlparse(reference)
    path = unquote(result.path)
    target = (source.parent / path).resolve() if path else source
    if target.is_dir():
        target = target / "index.html"
    return target, unquote(result.fragment)


for name in ("index.html", "styles.css", "script.js", ".nojekyll",
             "robots.txt", "sitemap.xml", "favicon.svg", "README.md", "BRAND.md"):
    if not (SITE / name).is_file():
        ERRORS.append(f"Missing required file: site/{name}")

pages = sorted(SITE.rglob("*.html"))
if len(pages) < 6:
    ERRORS.append("Expected the landing page and at least five docs pages")

parsed_pages: dict[Path, PageParser] = {}
for page in pages:
    parser = PageParser()
    try:
        parser.feed(page.read_text(encoding="utf-8"))
    except Exception as exc:
        ERRORS.append(f"{page.relative_to(ROOT)}: HTML parsing error: {exc}")
        continue
    parsed_pages[page.resolve()] = parser
    label = str(page.relative_to(ROOT))
    if parser.lang != "en":
        ERRORS.append(f"{label}: missing lang=en")
    if not parser.title:
        ERRORS.append(f"{label}: missing title")
    if not parser.description or len(parser.description) < 50:
        ERRORS.append(f"{label}: missing/descriptive metadata")
    elif len(parser.description) > 160:
        ERRORS.append(f"{label}: meta description is {len(parser.description)} characters; limit is 160")
    if not parser.skip_link:
        ERRORS.append(f"{label}: missing skip link (href=\"#main\")")
    scenarios_dir = (SITE / "scenarios").resolve()
    if page.resolve().parent == scenarios_dir and page.name not in ("index.html", "results.html"):
        if not parser.motion_toggle:
            ERRORS.append(f"{label}: scenario detail page lacks a [data-motion-toggle] element")
    if parser.h1 != 1:
        ERRORS.append(f"{label}: expected exactly one H1, got {parser.h1}")
    relative_url = page.relative_to(SITE).as_posix()
    if relative_url.endswith("index.html"):
        relative_url = relative_url[:-len("index.html")]
    expected_url = BASE_URL + relative_url
    if parser.canonical != expected_url:
        ERRORS.append(f"{label}: canonical mismatch ({parser.canonical} vs {expected_url})")
    if parser.duplicates:
        ERRORS.append(f"{label}: duplicate ids {parser.duplicates}")
    if parser.alt_missing:
        ERRORS.append(f"{label}: images without alt: {parser.alt_missing}")
    for block_number, block in enumerate(parser.jsonld, start=1):
        try:
            json.loads(block)
        except json.JSONDecodeError as exc:
            ERRORS.append(f"{label}: invalid JSON-LD block {block_number}: {exc}")
    for ref in parser.links + parser.assets:
        if ref.startswith(("http:", "https:", "mailto:", "tel:", "javascript:")):
            continue
        path, fragment = local_target(page, ref)
        try:
            path.relative_to(SITE.resolve())
        except ValueError:
            ERRORS.append(f"{label}: link exits published site: {ref}")
            continue
        if not path.is_file():
            ERRORS.append(f"{label}: missing linked target: {ref}")
        elif fragment and path.suffix == ".html":
            linked = parsed_pages.get(path)
            if linked is None:
                # Defer forward references until all page files are parsed.
                continue
            if fragment not in linked.ids:
                ERRORS.append(f"{label}: missing fragment {ref}")

# Second pass resolves HTML references to pages parsed later in sort order.
for page, parser in parsed_pages.items():
    for ref in parser.links:
        if ref.startswith(("http:", "https:", "mailto:", "tel:")):
            continue
        target, fragment = local_target(page, ref)
        if fragment and target.suffix == ".html" and target in parsed_pages:
            if fragment not in parsed_pages[target].ids:
                message = f"{page.relative_to(ROOT)}: broken fragment {ref}"
                if message not in ERRORS:
                    ERRORS.append(message)

social_png = SITE / "assets/social-card.png"
if not social_png.is_file():
    ERRORS.append("Missing social preview PNG")
else:
    png_head = social_png.read_bytes()[:24]
    if len(png_head) < 24 or png_head[:8] != b"\x89PNG\r\n\x1a\n":
        ERRORS.append("Invalid PNG signature")
    else:
        width = int.from_bytes(png_head[16:20], "big")
        height = int.from_bytes(png_head[20:24], "big")
        if (width, height) != (1280, 640):
            ERRORS.append(f"Unexpected social card dimensions: {width}x{height}")
        if social_png.stat().st_size > 1024 * 1024:
            ERRORS.append("Social card exceeds 1 MiB")

for name in ("sitemap.xml", "favicon.svg", "assets/logo-mark.svg",
             "assets/brand-lockup.svg", "assets/social-card.svg", "assets/robotics-hero.svg"):
    path = SITE / name
    if not path.is_file():
        ERRORS.append(f"Missing SVG/XML: site/{name}")
        continue
    try:
        ET.parse(path)
    except ET.ParseError as exc:
        ERRORS.append(f"site/{name}: invalid XML: {exc}")

sitemap = SITE / "sitemap.xml"
if sitemap.exists():
    try:
        root = ET.parse(sitemap).getroot()
        namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls = {e.text for e in root.findall(".//s:loc", namespace)}
        expected = {p.canonical for p in parsed_pages.values()}
        if urls != expected:
            ERRORS.append(f"Sitemap mismatch: missing={sorted(expected - urls)}, unexpected={sorted(urls - expected)}")
    except ET.ParseError:
        pass

robots = SITE / "robots.txt"
if robots.exists() and "Sitemap: " + BASE_URL + "sitemap.xml" not in robots.read_text(encoding="utf-8"):
    ERRORS.append("robots.txt: sitemap address does not match public base URL")


# Research scenario registry: proposed experiments must not masquerade as measurements.
# File/schema checks are necessary but cannot prove that a linked result was actually run.
registry_path = SITE / "scenarios/data/experiments.json"
if not registry_path.is_file():
    ERRORS.append("Missing site/scenarios/data/experiments.json")
else:
    try:
        import math
        record = json.loads(registry_path.read_text(encoding="utf-8"))
        if record.get("schema_version") != "scenario-results-v0":
            ERRORS.append("Scenario registry schema_version must be scenario-results-v0")
        items = record.get("experiments", [])
        expected_ids = {"fault-triage", "placement", "skill-review", "fleet-dispatch"}
        seen_ids: set[str] = set()
        if not isinstance(items, list):
            ERRORS.append("Scenario registry experiments must be a list")
            items = []
        for item in items:
            if not isinstance(item, dict):
                ERRORS.append("Scenario registry entry is not an object")
                continue
            ident = item.get("id")
            status = item.get("status")
            if not isinstance(ident, str) or ident not in expected_ids or ident in seen_ids:
                ERRORS.append(f"Scenario registry invalid/duplicate id: {ident!r}")
            if isinstance(ident, str):
                seen_ids.add(ident)
            if status not in ("planned", "collecting", "verified"):
                ERRORS.append(f"{ident}: invalid status: {status!r}")
            if not isinstance(item.get("primary_metric"), str) or not item["primary_metric"].strip():
                ERRORS.append(f"{ident}: missing primary_metric")
            if not isinstance(item.get("unit"), str) or not item["unit"].strip():
                ERRORS.append(f"{ident}: missing unit")
            evidence_fields = ("evidence_url", "run_manifest_sha256", "source_commit",
                               "raw_data_url", "analysis_script_url", "reviewed_by", "review_date_utc")
            if status != "verified":
                if item.get("result") is not None:
                    ERRORS.append(f"{ident}: unverified status must keep result null")
                if item.get("run_count") != 0:
                    ERRORS.append(f"{ident}: unverified status must have run_count=0")
                if any(item.get(key) is not None for key in evidence_fields):
                    ERRORS.append(f"{ident}: unverified status must not display result evidence")
            else:
                value = item.get("result")
                if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
                    ERRORS.append(f"{ident}: verified result must be a finite number")
                elif value < 0 or (item.get("unit") in ("fraction", "macro-F1") and value > 1):
                    ERRORS.append(f"{ident}: verified result outside expected nonnegative/unit range")
                if not isinstance(item.get("run_count"), int) or item.get("run_count") < 1:
                    ERRORS.append(f"{ident}: verified record needs observed run_count >= 1")
                for key in ("evidence_url", "raw_data_url", "analysis_script_url"):
                    if not isinstance(item.get(key), str) or not item[key].startswith("https://"):
                        ERRORS.append(f"{ident}: verified result missing HTTPS {key}")
                if not re.fullmatch(r"[a-fA-F0-9]{64}", str(item.get("run_manifest_sha256") or "")):
                    ERRORS.append(f"{ident}: missing immutable run_manifest_sha256")
                if not re.fullmatch(r"[a-fA-F0-9]{40}", str(item.get("source_commit") or "")):
                    ERRORS.append(f"{ident}: missing source_commit SHA")
                for key in ("reviewed_by", "review_date_utc"):
                    if not isinstance(item.get(key), str) or not item[key].strip():
                        ERRORS.append(f"{ident}: missing independent review metadata {key}")
                if not isinstance(item.get("limitations"), str) or not item["limitations"].strip():
                    ERRORS.append(f"{ident}: verified result must document limitations")
        if seen_ids != expected_ids:
            ERRORS.append(f"Scenario registry IDs: missing={sorted(expected_ids - seen_ids)}, extra={sorted(seen_ids - expected_ids)}")
    except (ValueError, TypeError, OSError) as exc:
        ERRORS.append(f"Invalid scenario registry JSON: {exc}")

if ERRORS:
    print("Static website validation failed:")
    for error in ERRORS:
        print(" - " + error)
    sys.exit(1)
print(f"Static website validation passed: {len(pages)} HTML pages, metadata, links, fragments, assets and sitemap.")
