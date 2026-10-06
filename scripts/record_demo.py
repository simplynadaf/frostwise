"""FrostWise demo recorder (v2).

Flow:
  - Intro chapter card
  - Hero (hold)
  - Scene banner (5s) -> scroll to planner
  - 3 real forecasts, each: banner (5s) describing the city, human-typed crop, click,
    WAIT for the real result, hold on it so the viewer reads the date + advice
  - Tour: How it works, Why open matters, footer
Everything uses the real local TabPFN + Gemma pipeline.

Banners use the Screencast overlay API (5-second holds). Typing uses per-char delay to
look human. Scrolling uses the browser's native smooth scroll.
"""
from playwright.sync_api import sync_playwright
import os, pathlib

OUT = "/tmp/frostwise-demo"
os.makedirs(OUT, exist_ok=True)
VIDEO = os.path.join(OUT, "frostwise-demo.webm")
URL = "http://127.0.0.1:8077/"

LOWER = lambda title, sub: f"""
<div style="position:fixed;bottom:46px;left:50%;transform:translateX(-50%);
  background:linear-gradient(135deg,rgba(11,15,22,.92),rgba(16,21,30,.92));
  backdrop-filter:blur(12px);border:1px solid rgba(156,198,230,.22);
  border-radius:14px;padding:16px 34px;text-align:center;
  font-family:-apple-system,Segoe UI,sans-serif;box-shadow:0 24px 70px rgba(0,0,0,.6);">
  <div style="font-size:22px;font-weight:700;color:#eef2f6;">{title}</div>
  <div style="font-size:15px;color:#9cc6e6;margin-top:5px;">{sub}</div>
</div>"""


def banner(page, title, sub, ms=5000):
    """Show a lower-third banner and HOLD it for ms (default 5s)."""
    ov = page.screencast.show_overlay(LOWER(title, sub))
    page.wait_for_timeout(ms)
    ov.dispose()


def scroll_to(page, sel, ms=1800):
    page.evaluate(f"document.querySelector('{sel}').scrollIntoView({{behavior:'smooth',block:'start'}})")
    page.wait_for_timeout(ms)


def run_forecast(page, station, crop, city_banner_sub):
    banner(page, f"Forecast {station}", city_banner_sub, 5000)
    page.select_option("#station", label=station)
    page.wait_for_timeout(1200)
    page.fill("#plant", "")
    page.type("#plant", crop, delay=110)          # human-paced typing
    page.wait_for_timeout(900)
    page.click("#go")
    # wait for the REAL frost date to render
    page.wait_for_function(
        "() => { const e=document.querySelector('#fd'); return e && e.textContent.trim().length>2; }",
        timeout=70000,
    )
    page.evaluate("document.getElementById('plan').scrollIntoView({block:'start'})")
    page.wait_for_timeout(7500)                    # hold on the result (read date + advice)


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(viewport={"width": 1440, "height": 810})
    pg = ctx.new_page()
    pg.screencast.start(path=VIDEO, size={"width": 1440, "height": 810})

    # Intro
    pg.goto(URL, wait_until="networkidle")
    pg.wait_for_timeout(1200)
    pg.screencast.show_chapter("FrostWise", description="Know when the frost lets go. Open-weight AI, fully offline.", duration=3200)
    pg.wait_for_timeout(2600)                       # hero + galaxy

    banner(pg, "One honest number: your last frost", "TabPFN-v2 forecasts it, Gemma 3 explains it, all on your laptop", 5000)
    scroll_to(pg, "#plan", 1900)

    # Three real forecasts across very different climates
    run_forecast(pg, "Miami, FL",   "basil",  "Warm south: effectively frost-free")
    run_forecast(pg, "Chicago, IL", "tomato", "Midwest: a real late-spring frost")
    run_forecast(pg, "Fargo, ND",   "peas",   "Far north: frost lingers into summer")

    # Tour
    banner(pg, "Two open models, one honest answer", "The forecast and the advice both run locally", 5000)
    scroll_to(pg, "#how", 2600)
    banner(pg, "Why open innovation matters", "Offline, private, free, and swappable", 5000)
    scroll_to(pg, "#why", 2600)
    pg.evaluate("window.scrollTo({top:document.body.scrollHeight,behavior:'smooth'})")
    pg.wait_for_timeout(2800)

    pg.screencast.stop()
    ctx.close(); b.close()

print("video:", VIDEO)
