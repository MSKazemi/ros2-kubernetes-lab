# ROS 2 Kubernetes Lab — GitHub Pages website

The static website for **ROS 2 Kubernetes Lab**, designed as an honest, accessible learning and research portal. The site is located under `site/` and does **not** rename or replace the public repository.

**Proposed live URL (verify after Pages deployment):** https://mskazemi.com/ros2-kubernetes-lab/

## What is included?

- **Landing page:** `site/index.html` — original branding, hero diagram, illustrative robotics art, project features, learning paths, setup tabs, technical roadmap and community entry points.
- **Visual identity:** `site/BRAND.md` — color tokens, logo assets, quotes, type, animation and truthful marketing rules.
- **Five HTML documentation pages:** `site/docs/` — hub, getting started, architecture, learning paths and contributing.
- **Roadmap:** `site/plans/` — a 90-day plan hub plus one animated page per phase (define the reference path, runnable and safe, package and document, grow with evidence) and a release-gates page. Content follows `docs/ROADMAP-2026.md`; every status is a proposal, and the animations show sequence, not progress.
- **Cloud–Edge Robotics Scenario Lab:** `site/scenarios/` — searchable gallery, four detailed Jev/ROS 2/Kubernetes research blueprints, each with its own short animated explainer (`#see-it`) and an interactive synthetic decision trace, plus a results status board and reproducibility registry. **Research proposals only, not live model results.**
- **Results governance:** `site/scenarios/data/experiments.json` starts with four planned records, all null performance values; `scripts/validate-site.py` rejects unverified result claims missing required provenance.
- **Collaboration/SEO playbooks:** `docs/scenario-lab/` with research issue map, Claude Code/Codex instructions, results publication standard and student-first SEO strategy.
- **Original graphics:** `site/assets/` — modular SVG mark, horizontal wordmark, robotics concept art, vector social preview and 1280×640 PNG social card.
- **Progressive enhancements:** `site/script.js` — mobile nav, working tabs, copy commands, architecture highlight, scroll reveal and an accessible pause-motion control.
- **Step animations:** `site/assets/lab-anim.js` and `lab-anim.css` — a small framework for CSS-driven step animations (see [Adding an animation](#adding-an-animation)). One CSS file per page in `site/assets/anim/`.
- **Styles:** `site/styles.css` for the home page, `site/assets/docs.css` for documentation.
- **SEO:** a unique title, description and canonical per page; `WebSite`/author structured data on the landing page and `BreadcrumbList` on every inner page; PNG Open Graph/Twitter metadata; `robots.txt`, an 18-URL sitemap, a served `llms.txt` and a `noindex` `404.html`.
- **Deploy and verify:** GitHub Actions in `.github/workflows/pages.yml`; offline validation in `scripts/validate-site.py`.

The website uses **vanilla HTML, CSS, and JS** (no npm build). External fonts are optional. There are no visitor analytics, user accounts, sales processing, or tracking cookies.

## Run locally

From repository root:

```bash
python3 -m http.server 8000 --directory site
# Visit http://localhost:8000
```

In a separate terminal:

```bash
python3 scripts/validate-site.py
node --check site/script.js
node --check site/assets/scenarios.js
node --check site/assets/lab-anim.js
```

The validator checks local site paths, document references, sitemap consistency, JSON-LD and XML well-formedness, unique `<title>` and meta description per page, `BreadcrumbList` on inner pages and `noindex` on the 404 page. It does not replace real browser testing, live network requests, accessibility review or Kubernetes/DDS integration tests.

### Visual checks before shipping

- Inspect at **360, 390, 768, 1024 and 1440 CSS pixels**; no horizontal scrolling or overlapping controls.
- Test desktop navigation, mobile menu, architecture layer highlights, tabs and both code-copy actions.
- Navigate all five documentation pages and their local anchor links.
- With `prefers-reduced-motion: reduce`, verify decorative animations stop and content remains visible.
- Click **Pause motion**, refresh and confirm the preference is respected.
- Check text, keyboard focus, image alternative text and readable code blocks.
- Check both light and dark browser/system themes for basic readability (the product deliberately uses a dark theme).

## Adding an animation

Every animation is a `<figure class="lab-anim">` with an inline SVG, a control bar and a list of steps. `lab-anim.js` only tracks which step is showing; it sets `data-step` and the cumulative classes `s-ge-0 … s-ge-N` on the figure, and your CSS draws the picture from those. Copy `site/plans/index.html` and `site/assets/anim/plans-hub.css` as the reference.

Rules every animation must follow:

- **No JS must still tell the whole story.** Write the base CSS so the figure without `.is-ready` shows the finished picture; the step list is plain text.
- **Reduced motion:** the framework never autoplays and `lab-anim.css` disables transitions; keep any extra motion short and optional.
- **Label it as an illustration.** No numbers, units or results that were not measured, and never colour alone: pair every status colour with a word.
- **Phones:** size SVG text in viewBox units so it renders at about 11 px or more at 390 px wide (the stage is about 325 px wide), or hide secondary labels at `max-width:640px`. The step cards below the figure carry the full text.
- Add the page to `sitemap.xml`; the validator checks it.

## Publish

1. Review and merge the website PR to `main` after checks pass. Per `AGENTS.md`, coding agents must **not** merge or push to `main` autonomously.
2. In repository **Settings → Pages → Build and deployment**, select **GitHub Actions** as publishing source (administrator action).
3. Run the `Deploy website to GitHub Pages` workflow or commit a site change to main.
4. Inspect the deployed website, all documentation pages, sitemap, favicon and console errors.
5. Only then set GitHub **About → Website** to the verified URL. Upload a raster social preview through Settings separately.

The workflow publishes **only the `site/` folder**; it does not expose analysis datasets, VM provisioning secrets, notebooks or Kubernetes credentials.

### Social preview

The designed card is `site/assets/social-card.svg` (vector source) and `site/assets/social-card.png` (1280×640 raster, under 1 MB). The website uses the PNG in Open Graph/Twitter metadata. An administrator must still upload the PNG in GitHub **Settings → Social preview**; publishing it in the repository does not configure GitHub's own social preview.

## Accuracy requirements

The historical Vagrant Kubernetes 1.29 / Weave Net / Foxy environment is **not** a current validated deployment. The newer ROS 2 Jazzy/Ubuntu 24.04 Dockerfile has an **image-local** talker/listener smoke test; cross-pod and cross-worker DDS communication are not established.

The robotics illustration is explicitly **concept art**. The architecture diagram is illustrative, not a live cluster feed. The website must not display manufactured adoption counts, testimonials, customer logos, production readiness, or performance claims. See the root `README.md`, `AGENTS.md`, `ROS2/jazzy/README.md` and the lab's open issues for source evidence.

This is an educational/research project and not a safety-critical robotics runtime or a paid service storefront.

## Growing the site

- **Technical docs source:** `site/docs/*.html`. Every page has distinct metadata and a stable canonical URL.
- **Brand source of truth:** `site/BRAND.md`.
- **Content/discoverability plan:** `docs/WEBSITE-GROWTH-AND-CONTENT.md`.
- **Full future documentation system:** issue [#19](https://github.com/MSKazemi/ros2-kubernetes-lab/issues/19) remains open for versioned MkDocs if/when a static multi-page site becomes insufficient.
- **Status changes:** verify end-to-end behavior and update README, guides, labels and site in one reviewed PR.
- **Changing the repo name/domain:** update every canonical, sitemap and robots entry and check GitHub redirects.

## License and safety

The project is distributed under [Apache-2.0](../LICENSE). Read [DISCLAIMER.md](../DISCLAIMER.md), [SAFETY.md](../SAFETY.md) and [SECURITY.md](../SECURITY.md) before applying historical configurations.
