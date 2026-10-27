# Student-first technical SEO and research visibility plan

> **SEO is a measured discovery process, not a promise of rankings, 20× growth or instant followers.** Never create fake scientific results or repeat low-value templated pages merely to target keywords. Revisit this plan after actually collecting Search Console data. Status of Pages deployment must be checked independently.

## 1. Audiences and conversion goals

| Audience | Query intent | Main landing page | Useful next action |
| --- | --- | --- | --- |
| ROS 2 beginners | "ROS 2 QoS mismatch Kubernetes", "DDS discovery troubleshooting" | [S1 diagnosis](../../site/scenarios/ros2-fault-triage.html) | Read synthetic case, contribute casebook #84 |
| MSc edge AI students | "ROS2 edge cloud inference latency", "robotics placement benchmark" | [S2 placement](../../site/scenarios/edge-cloud-inference.html) | Review network fault matrix #85 |
| LLM/robotics safety researchers | "LLM ROS2 agent safety", "robot skill validation" | [S3 agent review](../../site/scenarios/robot-agent-safety.html) | Evaluate prompt injection and policy tests #86 |
| Fleet/OR research students | "multi robot scheduling fairness simulation", "robot task allocation" | [S4 dispatch](../../site/scenarios/multi-robot-scheduling.html) | Propose synthetic scheduler study #87 |
| Research software engineers | "robotics reproducibility benchmark results" | [Evidence board](../../site/scenarios/results.html) | Submit provenance-complete result #88 |
| University instructors | "cloud robotics exercises for students" | [Scenario hub](../../site/scenarios/index.html) | Adapt BSc/MSc/PhD learning path, open collaboration #83 |

Treat these as candidate search phrases, **not verified keyword volumes or rankings**. Use real Search Console queries to refine language once indexed.

## 2. Technical SEO already designed for the scenario pages

- Unique, human-readable `<title>`, `<h1>`, meta descriptions; no keyword stuffing.
- Stable, accurate canonical URLs under the site's existing `/Vagrant-Kubernetes-ROS2-Deployment/` base. **Do not** change to `github.io` or another domain without verifying deployment and planning redirects/canonical updates.
- Semantic static HTML content with hypotheses, methods, metrics, evidence limitations and human contribution links. Animations are progressive enhancement and not the only place where information exists.
- BreadcrumbList schema.org JSON-LD and suitable `CollectionPage`/`TechArticle` types; structured data does **not** guarantee enhanced search results.
- Main homepage and docs link to scenario hub and detailed pages; internal scenario cross-links use descriptive anchor text; sitemap enumerates all exact pages.
- Consistent original Open Graph raster card, HTML language, mobile viewport, visible link labels and alt/ARIA on concept SVG.
- No visitor tracking, cookies or scripts fetching real robot telemetry. Browser JavaScript makes only optional same-origin fetch of the public synthetic experiment registry.

**Release audit:** `python3 scripts/validate-site.py`, `node --check site/assets/scenarios.js`, real browser review (360/390/768/1024/1440px, keyboard, pausable/reduced motion, dark theme contrast), clean console and live canonical URLs. GitHub Actions CI should show passes *before* merging; verify actual Pages deployment and crawlability after merge.

## 3. Student content that creates genuine value

Publish fewer, more original pages with real casebooks and source/research artifacts.

1. A reproducible *synthetic* ROS 2 QoS puzzle with solution rationale and a caveat about ambiguous DDS/network symptoms.
2. A network-impairment classroom exercise showing how eligibility must reject disconnected cloud services **before** model preference.
3. An agentic skills exercise asking students to distinguish deterministic authorization from probabilistic screening.
4. A fleet scheduling worksheet comparing capability/fairness filters with optional advisory selection.
5. A results report with reproducibility and limitations, only after a real study has been run.
6. Future interactive workshops/short walkthrough video only from accurately labelled synthetic simulation and permission-cleared assets.

Where possible link the homepage, learning-path docs, relevant GitHub issue, exact source code, experiment manifest and the evidence page with descriptive text. Encourage legitimate questions and collaborations; avoid promotional copy in technical support communities without useful context.

## 4. Ethical outreach and collaboration

- Comment substantively on relevant ROS 2 Discourse, GitHub issue/discussion and university teaching communities where on-topic posting and self-links are allowed. A helpful answer should remain useful even with the project link removed.
- Share a concise student research invitation: specific open problem, no GPU requirement, what contribution is welcome and reproducibility expectations.
- Link direct scenario URLs (not only the repository root) when the topic matches. Do not mass-spam, scrape contacts, automate bulk comments, impersonate researchers or claim third-party endorsement.
- Offer legitimate collaboration roles: dataset reviewer, teaching assistant, simulator expert, network researcher, reproducibility reviewer, frontend accessibility contributor.
- Only offer credits/authorship according to the real, documented contribution and academic publication policies; no guaranteed academic authorship from filing an issue.
- Cross-link relevant Hugging Face/model/dataset work **after** licenses, embodiment compatibility and a working demo are established. Avoid unverified claims.

## 5. Search performance and student adoption measurement

**Baseline period:** after verifying a real live site and connecting authorized Search Console for the right canonical property. Never invent zero-day traffic, rankings or indexing.

| Signal | Source | Research-useful interpretation |
| --- | --- | --- |
| Indexed canonical scenario pages | Search Console / manual URL inspection | Is the intended site discoverable at all? |
| Impressions, search clicks, CTR and queries by page | Search Console | Which student intents lead to real visits? |
| GitHub issues opened and outside contributor PRs | Public GitHub Insights / Issues | Are readers engaging in meaningful technical work? |
| Exercise completion feedback, broken step reports | Issues / opt-in educator feedback | Can students actually finish an assignment? |
| Reproducible third-party results and citations | Reviewed published artifacts | Does the lab support independent research? |
| Mobile and keyboard usability regressions | Manual/browser tests and CI | Is the audience excluded by interaction design? |

Avoid storing user IDs, fingerprinting, invasive analytics or collecting individual student emails through the site. User privacy and academic ethics take priority over metrics.

## 6. 30/60/90-day editorial sequence (proposal, not promise)

**First period:** review and merge the scenario PR, verify live URLs/canonicals/sitemap and student usability, invite narrow feedback on one scenario. Track bugs in issue #89.

**Second period:** ship the offline-only S1 casebook and deterministic baseline through #74/#84; publish an educator walkthrough with real screenshots of *synthetic* cases after it works.

**Third period:** publish pre-registered comparisons with raw evidence through #75/#88 if the run is actually feasible; organize a legitimate lab collaboration/instructor call only with specific completed material.

Use source/evidence dates honestly. Do not update `dateModified` merely to suggest freshness.

## Official references
- [Google Search Essentials](https://developers.google.com/search/docs/essentials)
- [Google SEO starter guide](https://developers.google.com/search/docs/fundamentals/seo-starter-guide)
- [Google creating helpful people-first content](https://developers.google.com/search/docs/fundamentals/creating-helpful-content)
- [Google JavaScript SEO basics](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics)
- [Technical SEO and crawlability](https://developers.google.com/search/docs/fundamentals/get-started-developers)
