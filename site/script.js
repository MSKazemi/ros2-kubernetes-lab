(() => {
"use strict";
const modes={infra:"One control plane and two worker VMs in the historical VirtualBox network. Diagram is illustrative, not live telemetry.",dds:"Study ROS 2 communication and DDS discovery. Cross-worker message delivery has not yet been validated.",observe:"Explore historical Prometheus and Grafana configurations. This is not live monitoring."};
const lab=document.getElementById("labWindow"),desc=document.getElementById("diagramDescription");
document.querySelectorAll(".mode-button").forEach(b=>b.addEventListener("click",()=>{const m=b.dataset.mode;if(!modes[m])return;lab.dataset.mode=m;desc.textContent=modes[m];document.querySelectorAll(".mode-button").forEach(x=>{const active=x===b;x.classList.toggle("is-active",active);x.setAttribute("aria-pressed",String(active));});}));
const tabs=Array.from(document.querySelectorAll('[role="tab"][data-tab]'));
function activate(tab,focus=false){tabs.forEach(b=>{const active=b===tab;b.classList.toggle("is-active",active);b.setAttribute("aria-selected",String(active));b.tabIndex=active?0:-1;document.getElementById(b.getAttribute("aria-controls")).hidden=!active;});if(focus)tab.focus();}
tabs.forEach((tab,i)=>{tab.addEventListener("click",()=>activate(tab));tab.addEventListener("keydown",e=>{let next;if(e.key==="ArrowRight")next=(i+1)%tabs.length;else if(e.key==="ArrowLeft")next=(i+tabs.length-1)%tabs.length;else if(e.key==="Home")next=0;else if(e.key==="End")next=tabs.length-1;if(next!==undefined){e.preventDefault();activate(tabs[next],true);}});});
const toggle=document.querySelector(".mobile-toggle"),nav=document.getElementById("site-nav");
function close(){nav.classList.remove("is-open");toggle.setAttribute("aria-expanded","false");toggle.setAttribute("aria-label","Open navigation");}
toggle.addEventListener("click",()=>{const open=nav.classList.toggle("is-open");toggle.setAttribute("aria-expanded",String(open));toggle.setAttribute("aria-label",open?"Close navigation":"Open navigation");});
nav.querySelectorAll("a").forEach(a=>a.addEventListener("click",close));document.addEventListener("keydown",e=>{if(e.key==="Escape")close();});
const toast=document.getElementById("copyToast");let timer;
function notify(message){toast.textContent=message;toast.classList.add("is-visible");clearTimeout(timer);timer=setTimeout(()=>toast.classList.remove("is-visible"),2600);}
document.querySelectorAll("[data-copy]").forEach(b=>b.addEventListener("click",async()=>{const target=document.getElementById(b.dataset.copy);if(!target)return;try{const text=target.textContent.trim();if(navigator.clipboard&&window.isSecureContext)await navigator.clipboard.writeText(text);else{const el=document.createElement("textarea");el.value=text;el.style.position="fixed";el.style.opacity="0";document.body.appendChild(el);el.select();const copied=document.execCommand("copy");el.remove();if(!copied)throw new Error("copy failed");}notify("Commands copied to clipboard");const span=b.querySelector("span");span.textContent="Copied";setTimeout(()=>span.textContent="Copy",2400);}catch{notify("Could not copy automatically. Select commands to copy.");}}));
document.getElementById("year").textContent=String(new Date().getFullYear());

const motionButton=document.querySelector(".motion-toggle");
const prefersReduced=window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const revealElements=[
  ...document.querySelectorAll(".section-head"),
  ...document.querySelectorAll(".feature-card"),
  ...document.querySelectorAll(".pathway-card"),
  ...document.querySelectorAll(".roadmap-card"),
  ...document.querySelectorAll(".resource-card"),
  ...document.querySelectorAll(".cinematic-overlay")
];
revealElements.forEach(el=>el.setAttribute("data-reveal",""));
let savedMotion=false;
try{ savedMotion=window.localStorage.getItem("ros2-lab-motion-paused")==="true"; }catch{}
let paused=prefersReduced||savedMotion;
function updateMotion(){
  document.documentElement.classList.toggle("motion-paused",paused);
  document.documentElement.classList.toggle("has-motion",!paused);
  if(motionButton){
    motionButton.setAttribute("aria-pressed",String(paused));
  }
  if(paused) revealElements.forEach(el=>el.classList.add("is-revealed"));
}
updateMotion();
if(motionButton){
  motionButton.addEventListener("click",()=>{
    paused=!paused;
    try{window.localStorage.setItem("ros2-lab-motion-paused",String(paused));}catch{}
    updateMotion();
  });
}
if("IntersectionObserver" in window){
  const observer=new IntersectionObserver(entries=>{
    for(const entry of entries){
      if(entry.isIntersecting){entry.target.classList.add("is-revealed");observer.unobserve(entry.target);}
    }
  },{threshold:.12,rootMargin:"0px 0px -20px 0px"});
  revealElements.forEach(el=>observer.observe(el));
}else{
  revealElements.forEach(el=>el.classList.add("is-revealed"));
}
})();