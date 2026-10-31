/* Lab animation framework: declarative, CSS-driven step animations.
 *
 * Markup contract (see site/plans/index.html):
 *   <figure class="lab-anim" data-anim="name" data-interval="2800">
 *     <div class="lab-anim__stage"><svg ...>visuals keyed on [data-step] / .s-ge-K</svg></div>
 *     <div class="lab-anim__bar"> buttons: data-anim-prev|play|next|replay, <output data-anim-status> </div>
 *     <ol class="lab-anim__steps"><li data-step-text><button type="button"><b>Title</b><span>Description</span></button></li>...</ol>
 *   </figure>
 *
 * JS only manages state. On every change it sets, on the figure:
 *   data-step="i"            exact 0-based step
 *   .s-ge-0 ... .s-ge-i      cumulative classes ("this step or later")
 *   .is-playing              while auto-advancing
 *   --step / --steps         CSS custom properties
 * and dispatches "labanim:step" ({detail:{step,count}}) for optional custom hooks.
 * Without JS the figure has no data-step, so CSS shows the finished state and the steps list is plain text.
 * Reduced motion: never autoplays; stepping is manual. The shared "paused" preference
 * (localStorage "scenarios-motion-paused") also blocks autoplay. */
(function () {
  "use strict";
  var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  function pausedPref() {
    try { return localStorage.getItem("scenarios-motion-paused") === "true"; } catch (_) { return false; }
  }

  function init(root) {
    var items = Array.prototype.slice.call(root.querySelectorAll("[data-step-text]"));
    var count = items.length;
    if (!count) return;
    var interval = parseInt(root.getAttribute("data-interval"), 10) || 2800;
    var status = root.querySelector("[data-anim-status]");
    var playBtn = root.querySelector("[data-anim-play]");
    var prevBtn = root.querySelector("[data-anim-prev]");
    var nextBtn = root.querySelector("[data-anim-next]");
    var replayBtn = root.querySelector("[data-anim-replay]");
    var at = 0, timer = null, started = false;

    function render() {
      root.setAttribute("data-step", String(at));
      root.style.setProperty("--step", String(at));
      root.style.setProperty("--steps", String(count));
      for (var k = 0; k < count; k++) root.classList.toggle("s-ge-" + k, k <= at);
      items.forEach(function (li, idx) {
        var btn = li.querySelector("button");
        li.classList.toggle("is-current", idx === at);
        li.classList.toggle("is-done", idx < at);
        if (btn) { if (idx === at) btn.setAttribute("aria-current", "step"); else btn.removeAttribute("aria-current"); }
      });
      if (status) status.textContent = "Step " + (at + 1) + " of " + count + ": " + titleOf(items[at]);
      if (prevBtn) prevBtn.disabled = at === 0;
      if (nextBtn) nextBtn.disabled = at === count - 1;
      root.dispatchEvent(new CustomEvent("labanim:step", { detail: { step: at, count: count } }));
    }
    function titleOf(li) { var b = li.querySelector("b"); return b ? b.textContent : li.textContent.trim(); }
    function setPlaying(on) {
      root.classList.toggle("is-playing", on);
      if (playBtn) {
        playBtn.setAttribute("aria-pressed", String(on));
        // Always available: play() restarts from the first step when the last one is showing.
        playBtn.querySelector("span").textContent = on ? "Pause" : "Play";
      }
    }
    function stop() { if (timer) { clearInterval(timer); timer = null; } setPlaying(false); }
    function go(i) { at = Math.max(0, Math.min(count - 1, i)); render(); if (at === count - 1) stop(); }
    function play() {
      if (at === count - 1) at = 0;
      render(); setPlaying(true);
      timer = setInterval(function () { if (at < count - 1) go(at + 1); else stop(); }, interval);
    }

    // Any visitor action wins over autoplay: once they touch a control, never auto-start.
    items.forEach(function (li, idx) {
      var btn = li.querySelector("button");
      if (btn) btn.addEventListener("click", function () { started = true; stop(); go(idx); setPlaying(false); });
    });
    if (playBtn) playBtn.addEventListener("click", function () { started = true; if (timer) stop(); else play(); });
    if (prevBtn) prevBtn.addEventListener("click", function () { started = true; stop(); go(at - 1); setPlaying(false); });
    if (nextBtn) nextBtn.addEventListener("click", function () { started = true; stop(); go(at + 1); setPlaying(false); });
    if (replayBtn) replayBtn.addEventListener("click", function () { started = true; stop(); at = 0; play(); });

    if (reduced) root.classList.add("is-reduced");
    root.classList.add("is-ready");
    go(reduced ? count - 1 : 0);          // reduced motion: show the complete picture; steps stay navigable
    setPlaying(false);

    // Autoplay once, when at least 45% visible, unless motion is reduced or paused by the visitor.
    if ("IntersectionObserver" in window && !reduced) {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          if (e.isIntersecting && !started && !pausedPref()) { started = true; play(); }
          if (!e.isIntersecting && timer) stop();
        });
      }, { threshold: 0.45 });
      io.observe(root);
    }
    document.addEventListener("visibilitychange", function () { if (document.hidden) stop(); });
  }

  function boot() { Array.prototype.forEach.call(document.querySelectorAll(".lab-anim"), init); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot); else boot();
})();
