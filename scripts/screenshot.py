from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1).new_page()
    pg.goto("http://127.0.0.1:8077/", wait_until="networkidle")
    pg.wait_for_timeout(3500)  # let 3D + reveals settle
    pg.screenshot(path="/tmp/fw_hero.png")
    # scroll to planner and run a forecast
    pg.evaluate("document.getElementById('plan').scrollIntoView()")
    pg.wait_for_timeout(1500)
    pg.screenshot(path="/tmp/fw_planner.png")
    pg.click("#go")
    pg.wait_for_timeout(14000)  # wait for TabPFN + Gemma
    pg.screenshot(path="/tmp/fw_result.png")
    # scroll through lower sections
    pg.evaluate("document.getElementById('why').scrollIntoView()")
    pg.wait_for_timeout(1500)
    pg.screenshot(path="/tmp/fw_why.png")
    b.close()
print("shots done")
