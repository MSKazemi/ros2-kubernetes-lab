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
BASE_URL = "https://mskazemi.github.io/Vagrant-Kubernetes-ROS2-Deployment/"
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
        self.jsonld: list[str] = []
        self._inside_ld = False

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

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self._inside_ld = False

    def handle_data(self, data: str) -> None:
        if self._inside_ld:
            self.jsonld.append(data)


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
    if parser.h1 != 1:
        ERRORS.append(f"{label}: expected exactly one H1, got {parser.h1}")
    expected_url = BASE_URL + ("" if page == SITE / "index.html"
                               else page.relative_to(SITE).as_posix())
    if parser.canonical != expected_url:
        ERRORS.append(f"{label}: canonical mismatch ({parser.canonical} vs {expected_url})")
    if parser.duplicates:
        ERRORS.append(f"{label}: duplicate ids {parser.duplicates}")
    if parser.alt_missing:
        ERRORS.append(f"{label}: images without alt: {parser.alt_missing}")
    if parser.jsonld:
        try:
            json.loads("".join(parser.jsonld))
        except json.JSONDecodeError as exc:
            ERRORS.append(f"{label}: invalid JSON-LD: {exc}")
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

if ERRORS:
    print("Static website validation failed:")
    for error in ERRORS:
        print(" - " + error)
    sys.exit(1)
print(f"Static website validation passed: {len(pages)} HTML pages, metadata, links, fragments, assets and sitemap.")
