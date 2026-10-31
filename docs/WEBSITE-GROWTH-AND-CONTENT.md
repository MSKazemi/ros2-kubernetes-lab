# Website growth, scale, discoverability and sustainable collaboration

> ROS 2 Kubernetes Lab — 2026-10-27. This is a **plan and content policy**, not evidence of web traffic, sales or a finished research deployment. Public repository: https://github.com/MSKazemi/ros2-kubernetes-lab

## North star

The website exists to help *real people run a suitable experiment, learn a concept, reproduce evidence or contribute*. The goal is qualified visitors, successful learning outcomes and research collaboration—not vanity traffic or misleading marketing.

**Proposed user journey:** Search or social post → landing page → accurate capability/status explanation → one runnable entry point or lesson → documentation → reproducible result → contribution/citation/collaboration.

Distinguish the **scale of the website** (load, maintenance, content growth, SEO) from possible **commercialization** (training, professional services). Neither website popularity nor sales are guaranteed, and the repository is not currently a storefront.

## Primary audiences and conversion journeys

| Audience | Search/intention | Entry | Desirable next action |
|---|---|---|---|
| Robotics student | ROS 2 on Kubernetes tutorial | `site/docs/getting-started.html` | Build/test the Jazzy container and report a verified learning outcome |
| Educator | Cloud robotics course / lab | `site/docs/lab-paths.html#educators` | Adapt exercises and suggest an instructional improvement |
| PhD researcher | DDS discovery across Kubernetes pods | `site/docs/architecture.html#dds` | Propose a reproducible cross-worker experiment with controls |
| Platform engineer | Kubernetes ROS 2 orchestration | `site/docs/architecture.html` | Check scope, version matrix and open integration tasks |
| Open-source contributor | ROS2 Kubernetes issues | `site/docs/contribute.html` | Pick an issue and submit a tested scoped patch |
| Research/industry collaborator | ROS 2 distributed robotics testbed | Audience paths and GitHub issues | Open a non-sensitive, concrete collaboration proposal |

**No fabricated trust signals.** Do not show 2K GitHub stars, 100+ contributors, 50 tutorials, university endorsements, installations, customer logos or testimonials unless independently verified and timestamped.

## Search and content strategy

- Main landing page: **ROS 2 on Kubernetes**, **ROS 2 Kubernetes Lab**.
- Documentation pages use distinct primary intents:
  - Getting started: ROS 2 Jazzy Docker image tutorial / historical Vagrant cluster.
  - Architecture: ROS 2 DDS discovery, Kubernetes multi-node topology and CNI pitfalls.
  - Learning paths: cloud robotics lab for students / reproducible robotics experiments.
  - Contribute: open-source ROS 2 Kubernetes contributions, optional coding-agent workflow.
- Maintain descriptive titles, unique meta descriptions, canonical URLs, useful H1, readable text, alt descriptions, sitemap and robots.txt.
- Avoid keyword stuffing and duplicate thin pages. Publish real evidence and lessons before promotional posts.
- Track canonical links after a repository slug rename. Do **not** rename the repo just to optimize SEO without a redirect/citation migration plan.
- In GitHub About, set the site URL only after Pages is actually published.

### Editorial series (proposals, not completed demos)

1. ROS 2 node vs Kubernetes node: why terminology matters.
2. Why DDS discovery between Kubernetes pods can surprise you.
3. Talker/listener inside one Jazzy container: what the smoke test proves.
4. Historical Vagrant Kubernetes lab: lessons from old dependencies.
5. How to design a cross-worker DDS benchmark (without inventing a result).
6. Autoscaling stress workloads vs genuine ROS application performance.
7. Measuring crash/recovery correctly in cloud robotics.
8. Responsible agentic AI for robotics infrastructure: future experiments.
9. Packaging a ROS 2 inference node for cloud-edge experiments (proposal).
10. Student assignments using diagrams, source code and historical datasets.

**Promotion cadence suggestion:** one substantial technically supported tutorial every 2–4 weeks, with short excerpts adapted to Dev.to, LinkedIn, robotics discussions and appropriate communities. Respect forum rules; only include GitHub links when relevant and genuinely useful. No automated spam or invented test results.

## Website scalability and engineering

- Static GitHub Pages hosting with version-controlled HTML/CSS/JS; no servers, databases or build steps required for the current landing page.
- Keep large datasets and Jupyter outputs out of Pages: publish only `site/` to avoid giant downloads.
- Load original SVG illustrations as external assets and lazy-load below-the-fold art.
- Use CSS/IntersectionObserver for movement; avoid expensive WebGL/canvas by default.
- Check broken links, unique metadata, headings, accessible labels, sitemap and script syntax in CI.
- Use stable absolute canonical URLs and relative internal links that work under the repository subpath.
- If docs become large, consider a data-driven generator (MkDocs/Material or Astro) **only after** migration planning, link parity and preview tests. Existing issue #19 remains the docs scale-up tracker.
- Consider translation (Italian, Persian, Chinese, other target audiences) after English docs are stable and technical status is synchronized.
- Do not add browser analytics until a privacy notice, consent requirements, data retention and appropriate EU data protection review are complete.

### Performance and accessibility targets (not achieved measurements)

| Item | Proposed acceptance target | Evidence needed |
|---|---|---|
| Page speed | Lighthouse Performance >=90 on a representative desktop and mobile test | Report URL, device profile, date and runs |
| Accessibility | Lighthouse Accessibility >=95 plus keyboard/manual test | Audit record; automation alone does not prove compliance |
| Images | Meaningful alt and dimension attributes; avoid multi-MB autoplay video | Static validator and network audit |
| Mobile layout | No horizontal overflow at 360, 390, 768, 1024 px | Browser screenshots/manual inspection |
| Reduced motion | Respect OS preference and a pause toggle | Keyboard and emulation verification |
| Search | Correct live sitemap and canonical, indexed after submission | Search Console/Bing evidence, not a guessed ranking |

## Sales and monetization: ethical options only

The code remains Apache-2.0; the website is **not yet a product checkout**. Potential adjacent paths, if there is demand:

- Instructor-led workshops on containers, ROS 2 and Kubernetes with original teaching material.
- Sponsored/paid research engineering on reproducibility and tooling; disclose sponsors and publication boundaries.
- B2B consulting for cloud-native robotics architecture or DDS troubleshooting under a separate explicit agreement.
- Commissioned integration, migration, benchmark design, or mentoring, subject to capacity, safety constraints and conflicts.
- Open-source sponsorship to fund maintenance and contributor reviews, with transparent terms.

Do not create pricing tables, fake client logos, “book a demo” availability, paid offers or payment processors until an actual offering, legal/tax review, support scope and contact channel exist. Do not imply any paid purchaser gains proprietary ownership of already-licensed Apache-2.0 code. Always state what is—and is not—supported, especially around safety-critical robotics.

### A measured collaboration funnel

The present site routes visitors to verifiable GitHub entry points. A later collaboration page could accept proposals **through GitHub issues** with non-sensitive fields: intended educational/research goal, reproducibility requirements, constraints, and non-confidential example. Avoid encouraging private technical secrets in public forums. Only offer a private contact channel after its ownership, security and privacy arrangements are decided.

## Measurement loop

Track monthly after Pages is live (do not backfill invented measurements):
1. Search Console impressions, clicks, query CTR, coverage.
2. GitHub Insights visitors/clones and unique external referrers (if available).
3. Documentation navigation and referring pages using privacy-appropriate aggregate metrics.
4. Successful user-reported installations and meaningful issue resolutions.
5. External reproducibility reports and citations.
6. Qualified collaboration requests versus irrelevant outreach.

Use UTM parameters only for genuine attributable campaigns and avoid hidden data collection. Present changes as “observed”, “reported”, or “hypothesized” based on evidence.

## 30/60/90 day sequence (proposals)

### First 30 days
- Review and merge website PR, enable GitHub Actions Pages, verify live URL.
- Upload the committed 1280×640 `site/assets/social-card.png` in GitHub Settings after validating preview behavior.
- Verify mobile, keyboard, motion, redirects, crawling metadata and all links.
- Set GitHub About website only after the site resolves.
- Collect zero-day analytics baselines without claiming traffic.

### Days 31–60
- Complete modern ROS/DDS validation gates in #14/#15 before promising multi-worker demos.
- Publish two deep technical posts linked to real code and a genuine video demonstration if available.
- Improve docs after actual beginner friction; test contribution journey.
- Decide whether versioned docs build pipeline from #19 is warranted.

### Days 61–90
- Publish a credible research note and experiment protocol with raw evidence.
- Ask interested educators and ROS developers for specific feedback through permitted channels.
- Evaluate optional translation, sponsorship or workshops based on real demand.
- Review traffic and contributor feedback against baseline and revise priorities.

## Launch criteria

- [ ] Pages URL deployed and manually viewed on multiple browsers/screen sizes.
- [ ] Status statements reflect actual image-local vs cluster-level test coverage.
- [ ] Brand source and social-export workflow documented.
- [ ] Sitemap, robots, canonical tags and subpath internal links verified.
- [ ] Motion accessible; reduced-motion setting tested.
- [ ] No false endorsements, claims, vanity stats or client testimonials.
- [ ] At least one path from each audience leads to a real guide, source or issue.
- [ ] Search metrics gathered only once measurable.

## Cloud–Edge Robotics scenario research expansion (proposed October 2026)

A dedicated [scenario hub](../site/scenarios/index.html) and four [student-facing research pages](../docs/scenario-lab/README.md) are proposed as a credible alternative to generic promotional landing pages. The pages contain falsifiable hypotheses, animated **synthetic** process traces, controls, baseline comparisons, actual issue links and an [evidence registry](../site/scenarios/results.html) that reports **N/A** until verifiable runs exist. No Jev integration, cross-node DDS success or real robot performance is claimed.

Follow [scenario epic #83](https://github.com/MSKazemi/ros2-kubernetes-lab/issues/83), contributor issues #84–#89, and the dedicated [SEO/content plan](../docs/scenario-lab/SEO-CONTENT-PLAN.md). Verify public site availability, all canonical URLs, browser UX and Search Console ownership before announcing rankings/traffic or posting externally. Good SEO is durable student value and accurate experiments, not keyword stuffing or automated mass comments.
