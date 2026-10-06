"""Start server in-process, screenshot the homepage, stop server."""
import os, sys, time, socket, subprocess, signal, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
os.chdir(ROOT)
env = dict(os.environ, FROSTWISE_MODEL="gemma3:1b")

def up():
    with socket.socket() as s:
        s.settimeout(.5); return s.connect_ex(("127.0.0.1", 8077)) == 0

subprocess.run("pkill -9 -f 'uvicorn frostwise' 2>/dev/null", shell=True); time.sleep(2)
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "frostwise.api:app",
    "--host", "127.0.0.1", "--port", "8077"],
    stdout=open("/tmp/shot_srv.log", "w"), stderr=subprocess.STDOUT, env=env, preexec_fn=os.setsid)
try:
    for _ in range(40):
        if up(): break
        time.sleep(1)
    from playwright.sync_api import sync_playwright
    out = ROOT / "docs" / "screenshots"
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_context(viewport={"width": 1440, "height": 860}, device_scale_factor=2).new_page()
        pg.goto("http://127.0.0.1:8077/", wait_until="networkidle")
        pg.wait_for_timeout(3000)
        pg.screenshot(path=str(out / "homepage.png"))
        b.close()
    print("homepage.png saved")
finally:
    try: os.killpg(os.getpgid(srv.pid), signal.SIGTERM)
    except: pass
