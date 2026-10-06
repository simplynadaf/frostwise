"""Self-contained demo runner: starts the server as a child process, waits until it is
listening, warms the forecasts, records the demo, and tears the server down. One Python
process, so nothing depends on shell background jobs surviving."""
import os, sys, time, socket, subprocess, signal, json, urllib.request, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
os.chdir(ROOT)
env = dict(os.environ, FROSTWISE_MODEL="gemma3:1b")

def listening(port=8077):
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0

# kill stragglers
subprocess.run("pkill -9 -f 'uvicorn frostwise' 2>/dev/null", shell=True)
time.sleep(2)

print("starting server...")
server = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "frostwise.api:app", "--host", "127.0.0.1", "--port", "8077"],
    stdout=open("/tmp/fw_srv.log", "w"), stderr=subprocess.STDOUT, env=env,
    preexec_fn=os.setsid,
)
try:
    for _ in range(40):
        if listening():
            break
        time.sleep(1)
    if not listening():
        print("SERVER FAILED TO LISTEN"); sys.exit(1)
    print("server listening.")

    # warm the three forecasts
    warm = [
        dict(latitude=25.76, elevation_m=2, feb_mean_c=21, mar_mean_c=23, winter_min_c=7, plant="basil", station="Miami, FL"),
        dict(latitude=41.88, elevation_m=181, feb_mean_c=-2, mar_mean_c=4, winter_min_c=-16, plant="tomato", station="Chicago, IL"),
        dict(latitude=46.88, elevation_m=274, feb_mean_c=-9, mar_mean_c=-2, winter_min_c=-27, plant="peas", station="Fargo, ND"),
    ]
    for w in warm:
        try:
            req = urllib.request.Request("http://127.0.0.1:8077/api/forecast",
                data=json.dumps(w).encode(), headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=90).read()
        except Exception as e:
            print("warm warn:", e)
    print("warmed. recording...")

    # run the recorder in-process (import and call) so it shares this live server
    import importlib.util
    spec = importlib.util.spec_from_file_location("record_demo", ROOT / "scripts" / "record_demo.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)   # record_demo.py runs on import
    print("recording done.")
finally:
    try:
        os.killpg(os.getpgid(server.pid), signal.SIGTERM)
    except Exception:
        pass
    print("server stopped.")
