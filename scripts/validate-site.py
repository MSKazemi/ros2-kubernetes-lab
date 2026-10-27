#!/usr/bin/env python3
"""Offline validation of the static GitHub Pages landing page."""
from html.parser import HTMLParser
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

site = Path(__file__).resolve().parents[1] / "site"
errors = []
for name in ("index.html", "styles.css", "script.js", "favicon.svg", "robots.txt", "sitemap.xml", ".nojekyll", "README.md"):
    if not (site / name).is_file():
        errors.append("Missing asset: " + name)

class Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.references = []
        self.files = []
        self.duplicates = []
        self.description = False
        self.canonical = False
        self.title = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        ident = a.get("id")
        if ident:
            if ident in self.ids:
                self.duplicates.append(ident)
            self.ids.add(ident)
        if a.get("href", "").startswith("#"):
            self.references.append(a["href"][1:])
        if a.get("aria-controls"):
            self.references.append(a["aria-controls"])
        if a.get("href", "").startswith("./"):
            self.files.append(a["href"][2:])
        if a.get("src", "").startswith("./"):
            self.files.append(a["src"][2:])
        if tag == "meta" and a.get("name") == "description":
            self.description = bool(a.get("content"))
        if tag == "link" and a.get("rel") == "canonical":
            self.canonical = True
        if tag == "title":
            self.title = True

if (site / "index.html").exists():
    html = (site / "index.html").read_text(encoding="utf-8")
    p = Parser()
    p.feed(html)
    for ident in p.duplicates:
        errors.append("Duplicate ID: " + ident)
    for ident in p.references:
        if ident and ident not in p.ids:
            errors.append("Missing anchor/control: " + ident)
    for file in p.files:
        if not (site / file).is_file():
            errors.append("Missing linked asset: " + file)
    if not all((p.title, p.description, p.canonical)):
        errors.append("Missing title, description or canonical URL")
    for keyword in ("Jazzy", "historical", "cross-worker"):
        if keyword.lower() not in html.lower():
            errors.append("Missing limitation/status: " + keyword)
for file in ("sitemap.xml", "favicon.svg"):
    if (site / file).exists():
        try:
            ET.parse(site / file)
        except ET.ParseError as exc:
            errors.append(file + ": " + str(exc))
if errors:
    print("Validation errors:\n" + "\n".join(errors))
    sys.exit(1)
print("Site static checks passed.")
