# ROS 2 Kubernetes Lab website

Static, zero-build website in `site/` for the **ROS 2 Kubernetes Lab** project. It does not rename the existing GitHub repository.

## Run locally

```bash
python3 -m http.server 8000 --directory site
# Open http://localhost:8000/
python3 scripts/validate-site.py
```

The page uses vanilla HTML, CSS and JavaScript. No npm dependencies. External Google Fonts are optional; system fallback fonts are specified.

## Publish

1. Review and merge the website branch to `main`.
2. Repository Settings → Pages → Build and deployment → select **GitHub Actions** (requires repository administrator).
3. Run **Deploy website to GitHub Pages** from Actions or make a change under `site/` on `main`.
4. Verify https://mskazemi.github.io/Vagrant-Kubernetes-ROS2-Deployment/ and configure GitHub About → Website to that real URL.
5. GitHub social preview is a separate Settings upload. Committing an image will not set it automatically.

The workflow uploads only `site/` as a Pages artifact. `scripts/validate-site.py` checks asset references and page metadata, while Node checks JavaScript syntax. Keep canonical URL, sitemap and robots.txt in sync if the repo slug changes.

## Accuracy policy

The historical Vagrant Kubernetes 1.29 + Foxy/Weave Net lab is separate from the newer Jazzy image-local test. The website does not assert live cluster telemetry, validated DDS messaging between workers, current Kubernetes compatibility, or production/safety-critical robotics readiness. The architecture display is illustrative. Roadmap features link to open issues, not finished features. Refresh status labels only when integration evidence warrants it.

This is a project landing page, not yet a full versioned MkDocs documentation system (tracked under issue #19). Continue maintaining the full tutorial in README and component guides.
