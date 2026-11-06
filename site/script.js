(() => {
"use strict";
/* Progressive enhancement for the landing page and for documentation pages that load this file.
   Every feature looks up its own elements and does nothing when they are absent, so one script can
   serve pages with different markup. The pages stay readable with JavaScript disabled. */
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
const reducedQuery = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : null;
const toast = document.getElementById("copyToast");
let toastTimer;
function notify(message) {
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add("is-visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("is-visible"), 2600);
}
async function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) { await navigator.clipboard.writeText(text); return; }
  const el = document.createElement("textarea");
  el.value = text;
  el.setAttribute("readonly", "");
  el.style.cssText = "position:fixed;opacity:0;top:0;left:0";
  document.body.appendChild(el);
  el.select();
  const copied = document.execCommand("copy");
  el.remove();
  if (!copied) throw new Error("copy failed");
}

/* Landing page: hero diagram layer buttons */
const lab = document.getElementById("labWindow"), desc = document.getElementById("diagramDescription");
const modes = {
  infra: "One control plane and two worker VMs in the historical VirtualBox network. Diagram is illustrative, not live telemetry.",
  dds: "Study ROS 2 communication and DDS discovery. Cross-worker message delivery has not yet been validated.",
  observe: "Explore historical Prometheus and Grafana configurations. This is not live monitoring."
};
if (lab && desc) {
  $$(".mode-button").forEach(button => button.addEventListener("click", () => {
    const mode = button.dataset.mode;
    if (!modes[mode]) return;
    lab.dataset.mode = mode;
    desc.textContent = modes[mode];
    $$(".mode-button").forEach(other => {
      const active = other === button;
      other.classList.toggle("is-active", active);
      other.setAttribute("aria-pressed", String(active));
    });
  }));
}

/* Landing page: tabs (roving tabindex, arrow/Home/End keys) */
const tabs = $$('[role="tab"][data-tab]');
function activate(tab, focus = false) {
  tabs.forEach(item => {
    const active = item === tab;
    item.classList.toggle("is-active", active);
    item.setAttribute("aria-selected", String(active));
    item.tabIndex = active ? 0 : -1;
    const panel = document.getElementById(item.getAttribute("aria-controls"));
    if (panel) panel.hidden = !active;
  });
  if (focus) tab.focus();
}
tabs.forEach((tab, i) => {
  tab.addEventListener("click", () => activate(tab));
  tab.addEventListener("keydown", event => {
    let next;
    if (event.key === "ArrowRight") next = (i + 1) % tabs.length;
    else if (event.key === "ArrowLeft") next = (i + tabs.length - 1) % tabs.length;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = tabs.length - 1;
    if (next !== undefined) { event.preventDefault(); activate(tabs[next], true); }
  });
});

/* Landing page: mobile navigation.
   aria-expanded carries the state, so the accessible name stays constant. Escape closes the menu and
   returns focus to the button; so do an outside click, tabbing out of the header and leaving the
   phone breakpoint. Links stay in the DOM and are hidden by CSS only while the menu is closed. */
const toggle = $(".mobile-toggle"), nav = document.getElementById("site-nav");
if (toggle && nav) {
  const desktop = window.matchMedia ? window.matchMedia("(min-width: 611px)") : null;
  toggle.setAttribute("aria-label", "Navigation menu");
  const isOpen = () => nav.classList.contains("is-open");
  const setOpen = open => { nav.classList.toggle("is-open", open); toggle.setAttribute("aria-expanded", String(open)); };
  toggle.addEventListener("click", () => setOpen(!isOpen()));
  $$("a", nav).forEach(link => link.addEventListener("click", () => setOpen(false)));
  document.addEventListener("keydown", event => {
    if (event.key !== "Escape" || !isOpen()) return;
    const hadFocus = nav.contains(document.activeElement) || document.activeElement === toggle;
    setOpen(false);
    if (hadFocus) toggle.focus();
  });
  document.addEventListener("click", event => {
    if (isOpen() && !nav.contains(event.target) && !toggle.contains(event.target)) setOpen(false);
  });
  document.addEventListener("focusin", event => {
    const header = toggle.closest("header") || nav.parentElement;
    if (isOpen() && header && !header.contains(event.target)) setOpen(false);
  });
  if (desktop) {
    const onChange = event => { if (event.matches) setOpen(false); };
    if (desktop.addEventListener) desktop.addEventListener("change", onChange);
    else if (desktop.addListener) desktop.addListener(onChange);
  }
}

/* Copy buttons that name their source element with data-copy */
$$("[data-copy]").forEach(button => button.addEventListener("click", async () => {
  const target = document.getElementById(button.dataset.copy);
  if (!target) return;
  const label = $("span", button);
  try {
    await copyText(target.textContent.trim());
    notify("Commands copied to clipboard");
    if (label) { label.textContent = "Copied"; setTimeout(() => { label.textContent = "Copy"; }, 2400); }
  } catch {
    notify("Could not copy automatically. Select commands to copy.");
  }
}));

const year = document.getElementById("year");
if (year) year.textContent = String(new Date().getFullYear());

/* Documentation pages: a Copy button on every code block (added by script, so no-JS readers lose nothing) */
$$("main.doc-content pre").forEach((pre, index) => {
  const code = $("code", pre);
  if (!code || pre.dataset.noCopy !== undefined || pre.parentElement.classList.contains("doc-pre")) return;
  const wrap = document.createElement("div");
  wrap.className = "doc-pre";
  pre.parentNode.insertBefore(wrap, pre);
  wrap.appendChild(pre);
  const button = document.createElement("button");
  button.type = "button";
  button.className = "doc-copy";
  button.textContent = "Copy";
  button.setAttribute("aria-label", "Copy code block " + (index + 1));
  const status = document.createElement("span");
  status.className = "doc-sr-only";
  status.setAttribute("role", "status");
  button.addEventListener("click", async () => {
    try {
      await copyText(code.textContent.replace(/\s+$/, ""));
      button.textContent = "Copied";
      status.textContent = "Code block copied to clipboard";
    } catch {
      button.textContent = "Select and copy";
      status.textContent = "Could not copy automatically";
    }
    setTimeout(() => { button.textContent = "Copy"; status.textContent = ""; }, 2400);
  });
  wrap.appendChild(button);
  wrap.appendChild(status);
  /* A code block that scrolls sideways must be reachable by keyboard */
  const markScrollable = () => {
    if (pre.scrollWidth > pre.clientWidth + 1) {
      pre.setAttribute("tabindex", "0");
      pre.setAttribute("role", "region");
      pre.setAttribute("aria-label", "Code block " + (index + 1) + ", scrollable");
    } else {
      pre.removeAttribute("tabindex");
      pre.removeAttribute("role");
      pre.removeAttribute("aria-label");
    }
  };
  markScrollable();
  window.addEventListener("resize", markScrollable);
});

/* Documentation pages: layer filter for the architecture diagram.
   The buttons are hidden in the markup and revealed here; without JavaScript the full diagram and the
   table underneath show everything. aria-pressed carries the state; text status labels never rely on colour. */
$$("[data-layer-filter]").forEach(group => {
  const figure = document.getElementById(group.dataset.layerFilter);
  if (!figure) return;
  group.hidden = false;
  const buttons = $$("button[data-show]", group);
  buttons.forEach(button => button.addEventListener("click", () => {
    figure.dataset.show = button.dataset.show;
    buttons.forEach(other => other.setAttribute("aria-pressed", String(other === button)));
  }));
});

/* Motion preference: the OS setting wins by default; the Pause motion button stores an explicit choice. */
const motionButton = $(".motion-toggle");
const revealElements = [".section-head", ".feature-card", ".pathway-card", ".roadmap-card", ".resource-card", ".cinematic-overlay"]
  .flatMap(selector => $$(selector));
revealElements.forEach(el => el.setAttribute("data-reveal", ""));
let savedMotion = false;
try { savedMotion = window.localStorage.getItem("ros2-lab-motion-paused") === "true"; } catch { /* storage may be blocked */ }
let systemReduced = Boolean(reducedQuery && reducedQuery.matches);
let paused = systemReduced || savedMotion;
function updateMotion() {
  const root = document.documentElement;
  root.classList.toggle("motion-paused", paused);
  root.classList.toggle("has-motion", !paused);
  if (motionButton) motionButton.setAttribute("aria-pressed", String(paused));
  if (paused) revealElements.forEach(el => el.classList.add("is-revealed"));
}
updateMotion();
if (reducedQuery) {
  const onChange = event => { systemReduced = event.matches; paused = systemReduced || savedMotion; updateMotion(); };
  if (reducedQuery.addEventListener) reducedQuery.addEventListener("change", onChange);
  else if (reducedQuery.addListener) reducedQuery.addListener(onChange);
}
if (motionButton) {
  motionButton.addEventListener("click", () => {
    paused = !paused;
    savedMotion = paused;
    try { window.localStorage.setItem("ros2-lab-motion-paused", String(paused)); } catch { /* storage may be blocked */ }
    updateMotion();
  });
}
if (revealElements.length) {
  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (entry.isIntersecting) { entry.target.classList.add("is-revealed"); observer.unobserve(entry.target); }
      }
    }, { threshold: .12, rootMargin: "0px 0px -20px 0px" });
    revealElements.forEach(el => observer.observe(el));
  } else {
    revealElements.forEach(el => el.classList.add("is-revealed"));
  }
}
})();
