/* Scenario explainers. Vanilla JS, no network, no storage writes, no inference.
 *
 * This script only STEPS THROUGH a fixed, hand-authored storyboard that is already present in the HTML
 * (see the .xp markup in each scenario page). It computes nothing about robots, models or networks.
 * Without JS every case is visible as a plain ordered list; with JS one case is shown at a time.
 *
 * Markup contract:
 *   [data-xp]                         root
 *     ol.xp-flow > li[data-stage]     pipeline stages (static)
 *     article.xp-case[data-title][data-tag]   one case; data-tag = accepted|rejected|abstain|config-error|baseline
 *       li.xp-step[data-stage][data-outcome]  outcome = pass|reject|abstain|info|na
 *       .xp-verdict                   shown after the last step
 *   [data-xp-pick="case-id"]          optional links elsewhere on the page that select a case
 */
(function () {
  "use strict";
  var OUT = { pass: "passed", reject: "REJECTED", abstain: "ABSTAINED (needs more evidence)", info: "info", miss: "DEADLINE MISSED", na: "N/A (not run)" };
  var GLYPH = { pass: "\u2713", reject: "\u2715", abstain: "?", info: "\u00b7", miss: "!", na: "\u2013" };
  var TAG = { accepted: "Allowed", rejected: "Rejected", abstain: "Abstains", "config-error": "Rejected config", baseline: "Baseline" };
  var STEP_MS = 3200;

  var mq = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : null;
  function motionOff() {
    return (mq && mq.matches) || document.documentElement.getAttribute("data-sc-motion") === "paused";
  }

  function el(tag, attrs, text) {
    var n = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) { n.setAttribute(k, attrs[k]); });
    if (text != null) n.textContent = text;
    return n;
  }

  function init(root) {
    var cases = Array.prototype.slice.call(root.querySelectorAll(".xp-case"));
    if (!cases.length) return;
    var flow = root.querySelector(".xp-flow");
    var nodes = flow ? Array.prototype.slice.call(flow.querySelectorAll("[data-stage]")) : [];
    var ci = 0, si = 0, timer = null;

    // ---- build controls (only exist when JS runs) ----
    var group = el("fieldset", { "class": "xp-cases" });
    group.appendChild(el("legend", null, "Choose a case (" + cases.length + ")"));
    var pickers = cases.map(function (c, i) {
      var b = el("button", { type: "button", "aria-pressed": "false", "data-tag": c.getAttribute("data-tag") || "" });
      b.appendChild(el("b", null, c.getAttribute("data-title") || "Case " + (i + 1)));
      b.appendChild(el("small", null, c.getAttribute("data-tag-label") || TAG[c.getAttribute("data-tag")] || ""));
      b.addEventListener("click", function () { stop(); select(i, 0); });
      group.appendChild(b);
      return b;
    });
    root.insertBefore(group, cases[0]);

    var bar = el("div", { "class": "xp-bar", role: "group", "aria-label": "Storyboard controls" });
    var prev = el("button", { type: "button" }, "Back");
    var play = el("button", { type: "button", "aria-pressed": "false" }, "Play");
    var next = el("button", { type: "button" }, "Next");
    var reset = el("button", { type: "button" }, "Restart case");
    var status = el("p", { "class": "xp-status", role: "status", "aria-live": "polite", "aria-atomic": "true" });
    var hint = el("p", { "class": "xp-hint", id: (root.id || "xp") + "-hint" },
      "Keyboard: Left/Right arrows step, Home/End jump. Play is optional and never starts by itself.");
    [prev, play, next, reset, status, hint].forEach(function (n) { bar.appendChild(n); });
    root.appendChild(bar);
    root.classList.add("is-enhanced");

    function stepsOf(i) { return Array.prototype.slice.call(cases[i].querySelectorAll(".xp-step")); }

    function render(announce) {
      var steps = stepsOf(ci), cur = steps[si];
      cases.forEach(function (c, i) { c.hidden = i !== ci; });
      pickers.forEach(function (b, i) { b.setAttribute("aria-pressed", String(i === ci)); });
      steps.forEach(function (s, i) {
        s.classList.toggle("is-current", i === si);
        s.classList.toggle("is-done", i < si);
        s.classList.toggle("is-future", i > si);
        if (i === si) s.setAttribute("aria-current", "step"); else s.removeAttribute("aria-current");
      });
      var verdict = cases[ci].querySelector(".xp-verdict");
      if (verdict) verdict.hidden = si !== steps.length - 1;

      // pipeline: summarise what happened in each stage up to (and including) the current step
      var seen = {}, state = {};
      steps.forEach(function (s, i) {
        if (i > si) return;
        var st = s.getAttribute("data-stage");
        seen[st] = true;
        state[st] = s.getAttribute("data-outcome");
      });
      var activeStage = cur.getAttribute("data-stage");
      nodes.forEach(function (n) {
        var st = n.getAttribute("data-stage"), o = state[st];
        n.className = "";
        var mark = n.querySelector(".xp-mark");
        if (seen[st]) n.classList.add("is-seen", "st-" + o);
        if (st === activeStage) n.classList.add("is-active");
        if (mark) mark.textContent = seen[st] ? GLYPH[o] + " " + (OUT[o] || o).split(" ")[0].toLowerCase() : "";
      });

      prev.disabled = si === 0;
      next.disabled = si === steps.length - 1;
      var title = cur.querySelector("h4");
      var outcome = cur.getAttribute("data-outcome");
      status.textContent = "Case " + (ci + 1) + " of " + cases.length + ", step " + (si + 1) + " of " + steps.length +
        ": " + (title ? title.firstChild.textContent.trim() : "") + " \u2014 " + (OUT[outcome] || outcome) + ".";
      if (si === steps.length - 1 && verdict) status.textContent += " Final: " + verdict.textContent.replace(/\s+/g, " ").trim();
      var pressed = timer !== null;
      play.setAttribute("aria-pressed", String(pressed));
      play.textContent = pressed ? "Pause" : "Play";
      if (motionOff()) {
        play.disabled = true;
        hint.textContent = "Auto-play is off because motion is reduced or paused. Use Next and Back.";
      } else {
        play.disabled = false;
      }
    }

    function select(i, s) { ci = Math.max(0, Math.min(cases.length - 1, i)); si = Math.max(0, Math.min(stepsOf(ci).length - 1, s)); render(true); }
    function stop() { if (timer !== null) { clearInterval(timer); timer = null; } }
    function go(d) {
      var n = stepsOf(ci).length;
      if (si + d >= n) return;
      if (si + d < 0) { return; }
      si += d; render(true);
    }
    function startPlay() {
      if (motionOff()) return;
      if (si === stepsOf(ci).length - 1) si = 0;
      render(true);
      timer = setInterval(function () {
        if (motionOff() || si >= stepsOf(ci).length - 1) { stop(); render(false); return; }
        si += 1; render(true);
      }, STEP_MS);
      render(false);
    }

    prev.addEventListener("click", function () { stop(); go(-1); });
    next.addEventListener("click", function () { stop(); go(1); });
    reset.addEventListener("click", function () { stop(); select(ci, 0); });
    play.addEventListener("click", function () { if (timer !== null) { stop(); render(false); } else startPlay(); });

    cases.forEach(function (c, i) {
      stepsOf(i).forEach(function (s, k) {
        s.addEventListener("click", function (e) {
          if (e.target.closest("a")) return;
          stop(); select(i, k);
        });
      });
    });

    root.addEventListener("keydown", function (e) {
      if (e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
      if (e.target.closest && e.target.closest(".xp-cases")) return;
      if (e.key === "ArrowRight") { stop(); go(1); e.preventDefault(); }
      else if (e.key === "ArrowLeft") { stop(); go(-1); e.preventDefault(); }
      else if (e.key === "Home") { stop(); select(ci, 0); e.preventDefault(); }
      else if (e.key === "End") { stop(); select(ci, stepsOf(ci).length - 1); e.preventDefault(); }
    });

    // Links elsewhere on the page ("show this case") select a case and bring the player into view.
    Array.prototype.forEach.call(document.querySelectorAll("[data-xp-pick]"), function (a) {
      a.addEventListener("click", function (e) {
        var id = a.getAttribute("data-xp-pick");
        for (var i = 0; i < cases.length; i++) {
          if (cases[i].id === id) {
            e.preventDefault(); stop(); select(i, 0);
            root.scrollIntoView({ block: "start", behavior: motionOff() ? "auto" : "smooth" });
            pickers[i].focus({ preventScroll: true });
            return;
          }
        }
      });
    });

    function onMotionChange() { if (motionOff()) stop(); render(false); }
    if (mq) { if (mq.addEventListener) mq.addEventListener("change", onMotionChange); else if (mq.addListener) mq.addListener(onMotionChange); }
    if (window.MutationObserver) new MutationObserver(onMotionChange).observe(document.documentElement, { attributes: true, attributeFilter: ["data-sc-motion"] });
    document.addEventListener("visibilitychange", function () { if (document.hidden && timer !== null) { stop(); render(false); } });

    // Deep link: #xp-case-<id> opens that case.
    var h = (location.hash || "").slice(1);
    var start = 0;
    cases.forEach(function (c, i) { if (c.id === h) start = i; });
    select(start, 0);
  }

  function boot() { Array.prototype.forEach.call(document.querySelectorAll("[data-xp]"), init); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot); else boot();
})();
