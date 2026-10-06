"""Pre-compute real TabPFN + Gemma results for all 20 presets, bake to web/static-data.json.

This powers the GitHub Pages static demo: the UI reads these real, pre-rendered results
when there is no local backend. Nothing is faked, the numbers come from the actual models.
"""
import os, sys, json, time, socket, subprocess, signal, urllib.request, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
os.chdir(ROOT)
env = dict(os.environ, FROSTWISE_MODEL="gemma3:1b")
OUT = ROOT / "web" / "static-data.json"

CROPS = ["tomato", "peas", "basil"]

def up():
    with socket.socket() as s:
        s.settimeout(.5); return s.connect_ex(("127.0.0.1", 8077)) == 0

subprocess.run("pkill -9 -f 'uvicorn frostwise' 2>/dev/null", shell=True); time.sleep(2)
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "frostwise.api:app", "--host", "127.0.0.1", "--port", "8077"],
    stdout=open("/tmp/bake.log", "w"), stderr=subprocess.STDOUT, env=env, preexec_fn=os.setsid)
try:
    for _ in range(45):
        if up(): break
        time.sleep(1)
    assert up(), "server down"

    stations = json.loads(urllib.request.urlopen("http://127.0.0.1:8077/api/stations", timeout=5).read())["stations"]
    baked = {"stations": stations, "results": {}}

    for s in stations:
        name = s["station"]
        baked["results"][name] = {}
        for crop in CROPS:
            body = {k: s[k] for k in ["latitude", "elevation_m", "feb_mean_c", "mar_mean_c", "winter_min_c", "enso_index"]}
            body.update(plant=crop, station=name)
            req = urllib.request.Request("http://127.0.0.1:8077/api/forecast",
                data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
            d = json.loads(urllib.request.urlopen(req, timeout=120).read())
            baked["results"][name][crop] = d
            print(f"  {name:22s} {crop:8s} -> {d['forecast']['last_frost_date']} ({d['advice']['source']})")

    OUT.write_text(json.dumps(baked, indent=0))
    print(f"\nwrote {OUT} ({OUT.stat().st_size//1024} KB), {len(stations)} stations x {len(CROPS)} crops")
finally:
    try: os.killpg(os.getpgid(srv.pid), signal.SIGTERM)
    except: pass
