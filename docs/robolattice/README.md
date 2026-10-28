# RoboLattice Research Lab — platform positioning RFC (2026-10-28)

> **WORKING NAME, not a cleared trademark or launched product.** Current public project remains **ROS 2 Kubernetes Lab** at https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment. No domain, Hugging Face organization, trademark, repository rename, or external account has been reserved. Do not change public canonicals or project attribution based on this RFC.

## Positioning

**Proposed umbrella:** RoboLattice Research Lab
**Original tagline:** Connect robots. Place intelligence. Prove results.
**Searchable descriptor:** Open ROS 2, Kubernetes, Hugging Face and cloud-edge robotics research lab.

Do **not** market this as a production robot controller, an existing AI product, or a benchmark leader. It is an open educational/research testbed that currently combines a historical Vagrant/Kubernetes setup, a tested *same-container* Jazzy smoke path, DDS and monitoring studies, an existing research scenario website, and proposed HF/LeRobot experiments.

## Why separate brand from SEO

A coined name alone does not say what is being taught. Use **RoboLattice** for identity only after approval; use **ROS 2 on Kubernetes**, **LeRobot**, **embodied AI**, **cloud-edge inference**, and **robotics observability** in the clear H1, title, explanatory copy, schema.org and page slugs. Avoid keyword stuffing. Preserve the existing repository URL and citation history.

### Planned product navigation

1. **ROS 2 / Kubernetes Lab** — repeatable local environments and transport troubleshooting.
2. **Embodied AI Lab** — HF/LeRobot model/dataset compatibility; policies and perception are separate tracks.
3. **Cloud–Edge Experiment Lab** — guarded local/remote inference; deadline and network impairment evaluation.
4. **Robotics Observability & Evidence** — traces, provenance, reproducible results; verified runs only.
5. **Student Research Studio** — hardware-free exercises, thesis hypotheses and bounded contributor issues.

### Visual design RFC

Keep the existing site's deep-navy / aqua / lavender visual vocabulary initially. Experimental logo idea: an original four-vertex connected lattice with a central inference node and one displaced edge node (no similarity to ROS, Kubernetes or Hugging Face official marks). Describe the concept clearly as *illustrative*; do not imply model integration or runtime demonstration.

## Naming screen and release gate

See [issue #22](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/22) for candidate collision screen, alternatives, and a detailed clearance checklist. RoboLattice was not associated with an exact-name result in the limited GitHub/web searches of 2026-10-28. This **does not prove availability or legal clearance**.

Before adopting as an official brand:
- Human-verified EUIPO/TMview and WIPO searches (and any target-country registries), including phonetic and visual variants, applicable goods/services and dates. Do not scrape the WIPO database automatically; see its rules.
- Registrar-confirmed .com / .ai / .org status; GitHub, HF, PyPI, npm and social handles.
- Domain purchase and trademark filing only after a deliberate owner decision; no autonomous registrations.
- Decide single canonical site; plan redirects, GitHub Pages paths, badges, website navigation, social preview, sitemap, llms.txt, citations and README.
- Run actual browser QA, link check and accessibility review; publish only verified claims.

Useful official guidance: https://www.euipo.europa.eu/en/trade-marks/before-applying/availability and https://www.wipo.int/en/web/madrid-system/check-availability.

## Status snapshot on 2026-10-28

- Website research scenario PR #90 is merged; *this does not imply every proposed experiment works*.
- Hugging Face scenario PR #100 was closed without merge; do not claim those pages, Space templates or the benchmark exist on main.
- kind cross-worker ROS 2 PR #97 is open; the proposed new stack is **not** the same as the historical Vagrant deployment.
- HF research roadmap #92 and related issues #53–#62, #93–#99 already cover major implementation pieces.
- No physical robot, production deployment, licensed model-training result or HF Space is claimed by this RFC.

## Editorial template for pages

**H1:** [Specific research question using ROS 2 / Hugging Face / Kubernetes]  
**Intro:** Explain the exact learning outcome and prerequisites.  
**Architecture:** What data, what trust boundary, what safety controller.  
**Reproducible methodology:** upstream artifact IDs, revisions, test fixtures, metrics, exclusions.  
**Evidence:** Planned / collecting / verified, with uncertainty and raw data.  
**CTA:** Exact scoped GitHub issue and contribution level.  
**Metadata:** Distinctive page title (~50–60 chars), genuine description (~130–155 chars), canonical URL; no invented reviews, metrics or affiliations.

**Reviewers:** confirm trademark screening and technical state before adding the working name to public site HTML.
