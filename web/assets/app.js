// FrostWise app logic: smooth scroll (Lenis), scroll reveals (GSAP), station presets,
// and the forecast call with an animated counting result.

// ---- scroll ----
// We use the browser's NATIVE scroll (1:1 with the wheel, never stalls). A JS smooth-scroll
// library (Lenis) was removed because driving it off the GSAP ticker produced a
// "stall then rush" feel. Section links still glide via scroll-behavior:smooth in CSS.
gsap.registerPlugin(ScrollTrigger);

// Only now (JS confirmed running) do we allow .reveal to start hidden.
document.documentElement.classList.add('js-reveal');

const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

function showAll() {
  gsap.set('.reveal', { opacity: 1, y: 0 });
}

if (reduced) {
  showAll();
} else {
  // Hero (above the fold): animate in immediately on load, do NOT gate on scroll.
  const hero = gsap.utils.toArray('header .reveal');
  gsap.to(hero, { opacity: 1, y: 0, duration: 0.8, ease: 'power3.out', stagger: 0.08 });

  // Below-the-fold: reveal on scroll, with an onEnter + fallback so nothing stays hidden.
  gsap.utils.toArray('section .reveal, footer .reveal').forEach((el) => {
    gsap.to(el, {
      opacity: 1, y: 0, duration: 0.8, ease: 'power3.out',
      scrollTrigger: { trigger: el, start: 'top 90%' },
    });
  });

  // Safety net: if anything is still hidden after 2.5s (e.g. headless/odd viewport), force it.
  setTimeout(() => {
    document.querySelectorAll('.reveal').forEach((el) => {
      if (parseFloat(getComputedStyle(el).opacity) < 0.1) gsap.set(el, { opacity: 1, y: 0 });
    });
  }, 2500);
}

// ---- station presets ----
const sel = document.getElementById('station');
const FIELDS = ['latitude', 'elevation_m', 'feb_mean_c', 'mar_mean_c', 'winter_min_c', 'enso_index'];
let STATIONS = [];
let STATIC = null;        // baked data when running without a backend (S3/static host)

// Detect a live backend; if absent, load the pre-baked results (static host).
async function detectMode() {
  try {
    const r = await fetch('/api/health', { method: 'GET' });
    if (r.ok) return 'live';
  } catch (e) { /* no backend */ }
  try {
    const r = await fetch('static-data.json');
    STATIC = await r.json();
    return 'static';
  } catch (e) { return 'none'; }
}

async function loadStations() {
  const mode = await detectMode();
  if (mode === 'live') {
    try {
      const d = await (await fetch('/api/stations')).json();
      STATIONS = d.stations || [];
    } catch (e) { STATIONS = []; }
  } else if (mode === 'static') {
    STATIONS = STATIC.stations || [];
    // In static mode, show an honest banner once.
    showStaticNote();
  }
  sel.innerHTML = '<option value="-1">Custom (type your own)</option>' +
    STATIONS.map((s, i) => `<option value="${i}">${s.station}</option>`).join('');
  const def = STATIONS.findIndex((s) => s.station.includes('Chicago'));
  if (def >= 0) { sel.value = def; applyStation(def); }
}

function showStaticNote() {
  const note = document.createElement('div');
  note.style.cssText = 'margin-top:14px;font-size:12.5px;color:var(--muted);border:1px dashed var(--line);border-radius:10px;padding:10px 14px;background:rgba(156,198,230,.04)';
  note.innerHTML = 'Hosted preview: these are <b style="color:#9cc6e6">real pre-computed</b> TabPFN-v2 + Gemma results for the preset cities. The live models run on your own machine, clone the repo and <code>python run.py</code> for custom input, fully offline.';
  const panel = document.querySelector('#plan .panel');
  if (panel) panel.insertBefore(note, panel.firstChild);
}

function applyStation(i) {
  const s = STATIONS[i]; if (!s) return;
  for (const f of FIELDS) {
    const el = document.getElementById(f);
    if (el && s[f] !== undefined) el.value = Math.round(s[f] * 100) / 100;
  }
}
sel.addEventListener('change', (e) => { const i = +e.target.value; if (i >= 0) applyStation(i); });

// ---- forecast ----
const go = document.getElementById('go');
const result = document.getElementById('result');

go.addEventListener('click', async () => {
  const i = +sel.value;
  const station = (i >= 0 && STATIONS[i]) ? STATIONS[i].station : 'your location';
  const plant = (document.getElementById('plant').value || 'tomato').trim().toLowerCase();
  const payload = { station, plant };
  for (const f of FIELDS) payload[f] = parseFloat(document.getElementById(f).value);

  go.disabled = true; go.innerHTML = '<span class="spinner"></span> Thinking locally…';
  result.innerHTML = '<div class="empty"><span class="spinner"></span><br>Running TabPFN-v2, then Gemma…</div>';

  // Static host: serve the pre-baked result for this preset + crop.
  if (STATIC) {
    await new Promise((r) => setTimeout(r, 900)); // let the spinner read naturally
    const byStation = STATIC.results[station];
    let d = byStation && (byStation[plant] || byStation[Object.keys(byStation)[0]]);
    if (!d && byStation) d = byStation[Object.keys(byStation)[0]];
    if (d) {
      // if the typed crop is not baked, keep the real forecast but note the crop set
      renderResult(d);
    } else {
      result.innerHTML = '<div class="empty">Pick one of the preset cities to see a pre-computed result, or run it locally for any climate.</div>';
    }
    go.disabled = false; go.textContent = 'Forecast my frost';
    return;
  }

  try {
    const r = await fetch('/api/forecast', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
    });
    const d = await r.json();
    renderResult(d);
  } catch (e) {
    result.innerHTML = `<div class="empty">Something went wrong: ${e.message}</div>`;
  } finally {
    go.disabled = false; go.textContent = 'Forecast my frost';
  }
});

function renderResult(d) {
  const f = d.forecast, a = d.advice;
  const srcLabel = a.source === 'gemma'
    ? `Written locally by ${a.model} (open-weight)`
    : `Offline fallback (no model reachable) · rule-based`;
  result.innerHTML = `
    <div>
      <div style="font-size:13px;color:var(--muted);letter-spacing:.1em;text-transform:uppercase">${f.station} · last spring frost</div>
      <div class="frostdate" id="fd">${f.last_frost_date}</div>
      <div class="frostmeta">likely between <b style="color:#dcebff">${f.range_low}</b> and <b style="color:#dcebff">${f.range_high}</b></div>
      <span class="count">${f.days_from_now >= 0 ? f.days_from_now + ' days from today' : 'already passed this year'}</span>
      <div class="advice">
        <div class="who">🌱 Planting ${d.plant}</div>
        <p id="adv"></p>
        <div class="src">${srcLabel}</div>
      </div>
    </div>`;
  gsap.from('#fd', { opacity: 0, y: 16, duration: 0.6, ease: 'power3.out' });
  gsap.from('.advice', { opacity: 0, y: 16, duration: 0.6, delay: 0.1, ease: 'power3.out' });
  typewriter(document.getElementById('adv'), a.text);
}

function typewriter(el, text) {
  el.textContent = '';
  let i = 0;
  const step = () => { if (i <= text.length) { el.textContent = text.slice(0, i); i += 2; setTimeout(step, 12); } };
  step();
}

loadStations();

// ---- hero CTAs: native smooth scroll ----
document.getElementById('plan-btn')?.addEventListener('click', () => {
  document.getElementById('plan').scrollIntoView({ behavior: 'smooth' });
});
document.getElementById('how-btn')?.addEventListener('click', (e) => {
  e.preventDefault();
  document.getElementById('how').scrollIntoView({ behavior: 'smooth' });
});
