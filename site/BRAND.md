# ROS 2 Kubernetes Lab — visual identity and brand system

> **Status:** Website design system, October 2026. Brand applies to the educational ROS 2/Kubernetes repository and its GitHub Pages documentation. It does not certify any robotics deployment or rename the underlying repository.

## 1. Positioning

**Display name:** ROS 2 Kubernetes Lab  
**Short mark:** ROS 2 / K8S LAB  
**Editorial line:** **Build. Observe. Experiment.**  
**Alternate original quote:** “Build systems. Observe behavior. Discover what works.”  
**Long form:** An open-source educational and research laboratory for exploring ROS 2 containers, historical Kubernetes infrastructure, middleware networking, observability, and reproducible robotics experiments.

The name should communicate **practical learning** before implying a commercial product or established production robotics platform.

**Brand character:** precise, ambitious, approachable, research-minded, transparent, technical.  
**Avoid:** “production-ready,” “fully validated,” invented community counts, false testimonials, false benchmarks, promises of hard real-time behavior, and fictitious robot integrations.

## 2. Visual assets

| Asset | Repository path | Use |
|---|---|---|
| Primary modular mark | `site/assets/logo-mark.svg` | Navbar, docs, presentations, avatars |
| Horizontal lockup | `site/assets/brand-lockup.svg` | Wide contexts, conference slides, README graphics |
| Robotics concept art | `site/assets/robotics-hero.svg` | Website showcase; always label *illustrative concept art* |
| Social card source | `site/assets/social-card.svg` | Editable vector composition for future social design updates |
| Social card PNG | `site/assets/social-card.png` | Ready-to-upload 1280×640 raster social preview and Open Graph preview |
| Favicon | `site/favicon.svg` | Browser tab |

These SVGs are original assets for this repository. They depict **concepts**, not proven deployed machines or screenshots. Do not add third-party robotics or cloud trademarks without checking usage guidelines. Do not use manufacturer logos to imply endorsement.

### Logo usage

- Preserve the logo's proportions and clear space (minimum equal to one-quarter of the mark width).
- Mark minimum onscreen size: **24×24 CSS pixels** (recommended 31–36 px).
- Horizontal wordmark: recommended width **240–520 CSS px** depending on context.
- Prefer the deep navy background or a high-contrast neutral. Avoid busy photographic backdrops without a solid panel.
- Do not stretch, rotate the entire wordmark, clip edges, or apply intense continuous rotation.
- The geometric mark is an **original visual metaphor** for distributed nodes, not the official ROS/Open Robotics or Kubernetes logo.

## 3. Colors

| Semantic token | Hex | Intent |
|---|---|---|
| Void | `#080D18` | Main background |
| Deep panel | `#101B2E` | Cards and surfaces |
| Raised panel | `#142037` | Interactive surfaces |
| Divider | `#2B3A53` | Borders and separation |
| Ice | `#F1F5FC` | Primary headings |
| Mist | `#95A4BB` | Secondary copy (verify contrast at chosen size) |
| Signal Aqua | `#66EBDA` | Primary accent, links and controls |
| Orbit Blue | `#7397FF` | Infrastructure motifs |
| Nebula Lilac | `#A193FF` | Robotics/DDS motifs |
| Alert Amber | `#FFA66E` | Legacy warnings and caveats |

**Usage ratio (guideline):** ~75% dark neutral surfaces, 15% restrained cool accents, 10% white text/semantic details. Use color to clarify system layers, not to imply a feature works.

**Accessibility:** aim for WCAG AA (4.5:1 for normal text, 3:1 for large text and critical UI lines). Bright accents are suitable for dark surfaces; muted secondary colors need review at 11–12 px. Do not encode status solely through color.

## 4. Type and layout

- **Display:** Space Grotesk (system fallback sans-serif), weight 500–700, controlled negative tracking.
- **Body:** DM Sans (system fallback sans-serif), weight 400–700.
- **Code and small technical labels:** JetBrains Mono (system fallback monospace).
- Header/content width: **1200 px** max for landing page; docs container max **1220 px** with reading column around **850 px**.
- Base spacing unit: **4 px**. Components primarily use 8/12/16/24/32/48/64/96 px steps.
- Border radius: 7–12 px for cards; 15–18 px for feature showcases.
- Responsive design: mobile-first inspection at **360 / 390 / 768 / 1024 / 1440 px**.

## 5. Animation and interaction policy

**Motion's job:** reveal relationships, signal focus, and make the interface pleasant without slowing documentation.

Current effects:
1. Soft gradient aurora movement in the hero headline.
2. Subtle parallax drift for original robotics concept art.
3. Low-key DDS illustration pulses and signal indicators.
4. IntersectionObserver scroll reveals for sections and cards.
5. Interactive architecture layer highlights, tabs, mobile navigation, and clipboard feedback.
6. Step animations (`lab-anim`): short, user-controlled explainers on roadmap and scenario pages. They play once when scrolled into view, never loop, never autoplay under reduced motion, and are always labelled *Illustration*.

**Reduced motion:** honor `prefers-reduced-motion: reduce` automatically and provide the **Pause motion** control. No autoplay video, audio, scroll-jacking or continuous aggressive camera movement. Motion can be disabled without hiding content.

**Performance budgets (proposed CI gates):**
- No WebGL runtime or analytics SDK by default.
- Avoid large JavaScript frameworks for decorative effects.
- Prefer optimized SVG/WebP/AVIF, sized images, async decoding and lazy loading below the fold.
- Set explicit intrinsic image dimensions to limit layout shifts.
- Measure on real mobile emulation before claiming Lighthouse scores; **do not invent a measured score**.

## 6. Marketing and brand copy

Approved factual anchors:
- Local **three-VM historical Vagrant/VirtualBox** educational configuration.
- ROS 2 **Jazzy image-local** smoke test and an amd64 CI path.
- Historical Prometheus/Grafana, stress workload and Python/Jupyter examples.
- Open issues for modern DDS cross-worker validation, networking hardening and lightweight profiles.
- Apache-2.0 project license (check LICENSE for exact terms).

**Never write these unless validated:** “one-click fully working multi-node ROS 2,” “production robotics,” “autonomous deployment,” “thousands of users,” “real-time guaranteed,” or benchmark numbers without source data.

Proposed quotes are **original brand writing**; never put them in quotation marks with a named outside researcher or user unless they truly said them and approved use.

Suggested copy:
- “A robotics lab for the distributed-systems curious.”
- “Build systems. Observe behavior. Discover what works.”
- “From local containers to better questions about distributed robotics.”
- “A transparent lab, not a black-box demo.”

## 7. Brand in social publishing

- The SVG source `site/assets/social-card.svg` is **1280×640**; a corresponding raster PNG exists as `site/assets/social-card.png`.
- For GitHub Settings → Social preview, upload the checked-in `site/assets/social-card.png` after verifying the platform's current format and size requirements. This step is **manual**; committing the file does not set the repository's social preview.
- For blog, Dev.to, YouTube thumbnails and slide covers, reuse the same typographic contrast, modular mark and 4-color accent vocabulary.
- Always link the **canonical public repository**, and use the **GitHub Pages website** only once deployment is verified.
- On demo videos distinguish *historical screen recordings* from new runtime evidence.

## 8. Design/feature acceptance checklist

- [ ] Desktop/mobile visual review and readable text on 360 px wide screens.
- [ ] Keyboard navigation, focus, names/labels and reduced-motion behavior.
- [ ] No fake status, customer testimonials, adoption data or network diagrams labeled “live”.
- [ ] Works with JS disabled for reading and links; core docs remain standard HTML.
- [ ] Internal, relative paths work under GitHub Pages **repository subpath**.
- [ ] Correct canonical URL and sitemap after a repo/domain rename.
- [ ] New artwork has meaningful alt text or empty alt if decorative.
- [ ] No public credential, kubeconfig, token or personally identifying telemetry.
- [ ] Cross-worker DDS and new Kubernetes support status follows actual tests.

## 9. Source of truth

Landing page: `site/index.html`, `site/styles.css`, `site/script.js`  
Documentation: `site/docs/*.html`, `site/assets/docs.css`  
Publishing: `.github/workflows/pages.yml`  
Static QA: `scripts/validate-site.py`  
Project technical truth: root `README.md`, `AGENTS.md`, component READMEs, test scripts and GitHub issues.

Maintain the distinction between **planned** and **verified** features as a hard requirement.
