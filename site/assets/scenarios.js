/* Scenario Lab — all interactive traces are preauthored educational illustrations.
   No provider calls, simulated inference outputs, robot commands, cookies or analytics. */
(() => {
  "use strict";
  const reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let paused = reduced;
  try { paused = paused || localStorage.getItem("scenarios-motion-paused") === "true"; } catch (_) {}
  const motion = document.querySelector("[data-motion-toggle]");
  function renderMotion() {
    document.documentElement.dataset.scMotion = paused ? "paused" : "running";
    if (motion) {
      motion.setAttribute("aria-pressed", String(paused));
      motion.textContent = paused ? "Enable decorative motion" : "Pause decorative motion";
    }
  }
  if (motion) motion.addEventListener("click", () => {
    paused = !paused;
    try { localStorage.setItem("scenarios-motion-paused", String(paused)); } catch (_) {}
    renderMotion();
  });
  renderMotion();

  const filterButtons = Array.from(document.querySelectorAll("[data-filter]"));
  const query = document.querySelector("[data-scenario-search]");
  const cards = Array.from(document.querySelectorAll("[data-scenario-card]"));
  const filterStatus = document.querySelector("[data-filter-status]");
  const emptySearch = document.querySelector(".sc-no-results");
  let active = "all";
  function updateCards() {
    const term = query ? query.value.trim().toLowerCase() : "";
    let shown = 0;
    cards.forEach(card => {
      const types = (card.dataset.topics || "").split(" ");
      const haystack = (card.textContent || "").toLowerCase();
      const match = (active === "all" || types.includes(active)) && (!term || haystack.includes(term));
      card.hidden = !match;
      if (match) shown++;
    });
    if (filterStatus) filterStatus.textContent = String(shown) + " scenarios shown";
    if (emptySearch) emptySearch.hidden = shown !== 0;
  }
  filterButtons.forEach(btn => btn.addEventListener("click", () => {
    active = btn.dataset.filter;
    filterButtons.forEach(item => item.setAttribute("aria-pressed", String(item === btn)));
    updateCards();
  }));
  if (query) query.addEventListener("input", updateCards);
  updateCards();

  const examples = {
    "fault-triage": {
      qos: {
        observation: "Synthetic evidence: a fictional publisher offers best-effort reliability while a fictional subscriber requires reliable delivery. The fixtures do not include real ROS 2 traffic.",
        steps: [
          "Read a fabricated publisher/subscriber event record and its declared QoS settings.",
          "Code detects the explicit reliability mismatch and rejects any stale or malformed evidence.",
          "An optional Jev Choice would compare diagnostic categories. No Jev call or prediction occurs in this visual.",
          "A human checks the suggested diagnosis; only an offline read-only report is allowed."
        ]
      },
      ambiguous: {
        observation: "Synthetic evidence: listener reports no messages, but discovery, network, QoS and resource diagnostics are absent. The root cause is unknown.",
        steps: [
          "Read the missing-message report; record unavailable observations explicitly.",
          "Hard checks cannot establish a single root cause. Preserve the unknown label.",
          "If used, Jev may offer an advisory distribution; this page shows no made-up answer.",
          "Request additional evidence and human review. Never issue a Kubernetes or robot command."
        ]
      }
    },
    placement: {
      ready: {
        observation: "Hypothetical scenario: two candidate policy services are compatible and pass the resource/privacy checks. Network latency values are not measured here.",
        steps: [
          "Collect a synthetic observation and abstract workload constraints.",
          "Code filters eligible local and remote candidates using numeric and privacy rules.",
          "Jev could advise a qualitative preference among eligible placements. No placement is selected by this animation.",
          "A human evaluates the actual benchmark and deterministic scheduler before any simulator placement."
        ]
      },
      outage: {
        observation: "Hypothetical scenario: remote service is unavailable while local fallback is configured in a fictional simulator.",
        steps: [
          "Observe synthetic network-disconnection metadata from a controlled impairment profile.",
          "The eligibility gate removes disconnected remote service before any model is asked.",
          "Jev has no authority to restore or choose an ineligible remote service.",
          "A simulated hold or validated local fallback is a future test; no live behavior is demonstrated."
        ]
      }
    },
    "skill-review": {
      allowed: {
        observation: "Fictional operator request: 'Report the simulated robot's current status.' Proposed skill: get_status with no privileged parameters.",
        steps: [
          "Parse a synthetic high-level natural-language goal into a proposed skill record.",
          "Schema + deterministic allowlist independently recognize get_status as a non-actuating simulator skill.",
          "Jev may offer a second opinion on intent or ambiguity, but cannot grant permissions.",
          "Human review and simulator executor would act only under separate permissions; no action runs on this page."
        ]
      },
      blocked: {
        observation: "Fictional untrusted prompt tries to request arbitrary /cmd_vel output or shell execution. This is intentionally unauthorized.",
        steps: [
          "Read the unsafe proposal strictly as untrusted fixture text.",
          "Independent deterministic authorization rejects commands outside the approved high-level skill catalog.",
          "Any favorable Jev or LLM suggestion is ignored: models do not override the validator.",
          "Record a simulated rejection for review. There is no physical robot and nothing is executed."
        ]
      }
    },
    "fleet-dispatch": {
      camera: {
        observation: "Fictional task: inspect a marker. Scout has an approved camera capability; carrier cannot run this task; arm is reserved.",
        steps: [
          "Read synthetic task and fleet capability records.",
          "Code removes robots lacking camera capability or available capacity.",
          "Jev could rank remaining eligible robot IDs for semantic fit, without determining feasibility.",
          "The deterministic scheduler would apply fairness and reservations in a future simulator experiment."
        ]
      },
      energy: {
        observation: "Fictional delivery task: the only eligible carrier has a simulated low-battery event below the predeclared reserve.",
        steps: [
          "Read the synthetic delivery request and state of the hypothetical fleet.",
          "Hard battery reserve excludes the carrier; no eligible robot remains.",
          "Jev cannot override energy, safety, permission, reservation or resource constraints.",
          "Return NO_RECOMMENDATION and queue for human planning; no robot moves."
        ]
      }
    }
  };

  const walk = document.querySelector("[data-walkthrough]");
  if (walk) {
    const slug = walk.dataset.walkthrough;
    const cases = examples[slug] || {};
    const select = walk.querySelector("[data-example-select]");
    const observation = walk.querySelector("[data-observation]");
    const live = walk.querySelector("[data-step-status]");
    const buttons = Array.from(walk.querySelectorAll("[data-step-index]"));
    const descriptions = Array.from(walk.querySelectorAll("[data-step-description]"));
    const next = walk.querySelector("[data-next-step]");
    const play = walk.querySelector("[data-play-steps]");
    let at = 0;
    let timer = null;
    function stop() {
      if (timer !== null) { clearInterval(timer); timer = null; }
      if (play) { play.textContent = "Play walkthrough"; play.setAttribute("aria-pressed", "false"); }
    }
    function show(i) {
      if (i < 0 || i >= buttons.length) return;
      at = i;
      buttons.forEach((btn, pos) => {
        btn.setAttribute("aria-current", pos === i ? "step" : "false");
        btn.closest("li").classList.toggle("is-current", pos === i);
      });
      if (next) next.textContent = i === buttons.length - 1 ? "Restart steps" : "Next step";
      if (live) live.textContent = "Illustrative stage " + (i + 1) + " of " + buttons.length + ": " + buttons[i].querySelector("strong").textContent;
    }
    function refresh() {
      stop();
      const item = cases[select ? select.value : ""];
      if (!item) return;
      if (observation) observation.textContent = item.observation;
      descriptions.forEach((el, idx) => { if (item.steps[idx]) el.textContent = item.steps[idx]; });
      show(0);
    }
    if (select) select.addEventListener("change", refresh);
    buttons.forEach((btn, idx) => btn.addEventListener("click", () => { stop(); show(idx); }));
    if (next) next.addEventListener("click", () => { stop(); show((at + 1) % buttons.length); });
    if (play) play.addEventListener("click", () => {
      if (timer !== null) { stop(); return; }
      if (reduced || paused) { show((at + 1) % buttons.length); return; }
      show(0);
      play.textContent = "Stop walkthrough";
      play.setAttribute("aria-pressed", "true");
      timer = setInterval(() => {
        if (at === buttons.length - 1) { stop(); return; }
        show(at + 1);
      }, 1350);
    });
    document.addEventListener("visibilitychange", () => { if (document.hidden) stop(); });
    refresh();
  }

  const resultsRoot = document.querySelector("[data-results-board]");
  if (resultsRoot) {
    fetch("./data/experiments.json", { cache: "no-store" })
      .then(response => { if (!response.ok) throw new Error("registry unavailable"); return response.json(); })
      .then(data => {
        if (!data || data.schema_version !== "scenario-results-v0" || !Array.isArray(data.experiments)) throw new Error("invalid registry");
        data.experiments.forEach(rec => {
          if (!rec || typeof rec.id !== "string") return;
          const row = resultsRoot.querySelector('[data-result-id="' + rec.id + '"]');
          if (!row) return;
          const status = row.querySelector("[data-result-status]");
          const metric = row.querySelector("[data-result-metric]");
          const evidence = row.querySelector("[data-result-evidence]");
          const verified = rec.status === "verified" && rec.result !== null && typeof rec.result === "number" &&
            Number.isFinite(rec.result) && typeof rec.evidence_url === "string" &&
            rec.evidence_url.startsWith("https://") && typeof rec.run_manifest_sha256 === "string" &&
            /^[a-f0-9]{64}$/i.test(rec.run_manifest_sha256);
          if (status) status.textContent = verified ? "Verified run (review evidence)" : "Not measured";
          if (metric) metric.textContent = verified ? String(rec.result) + " " + rec.unit : "N/A";
          if (evidence && verified) {
            evidence.href = rec.evidence_url;
            evidence.textContent = "Inspect evidence";
            evidence.hidden = false;
          }
        });
      })
      .catch(() => {
        const note = document.querySelector("[data-registry-warning]");
        if (note) { note.hidden = false; note.textContent = "Experiment registry unavailable. Static not-measured labels remain authoritative."; }
      });
  }
})();
