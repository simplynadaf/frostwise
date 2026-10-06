"""FrostWise API: ties the open-weight stack together and serves the UI.

  POST /api/forecast  { latitude, elevation_m, feb_mean_c, mar_mean_c, winter_min_c,
                        enso_index, plant, station? }
    -> { forecast {...}, advice {text, source, model} }

  GET  /api/stations  -> built-in station presets (climate means)
  GET  /api/health    -> model + ollama status

Everything runs locally: TabPFN-v2 (CPU) + Gemma via Ollama. No external calls.
"""
from __future__ import annotations
import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from frostwise.forecast import FrostModel, FEATURES
from frostwise.advice import advise, MODEL

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")

app = FastAPI(title="FrostWise", version="1.0.0")
_model = FrostModel()


class ForecastIn(BaseModel):
    latitude: float
    elevation_m: float
    feb_mean_c: float
    mar_mean_c: float
    winter_min_c: float
    enso_index: float = 0.0
    plant: str = "tomato"
    station: str = "your location"


@app.get("/api/health")
def health():
    import urllib.request
    ollama_ok = False
    try:
        urllib.request.urlopen(os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434") + "/api/tags", timeout=3)
        ollama_ok = True
    except Exception:
        ollama_ok = False
    return {"status": "ok", "model": MODEL, "ollama": ollama_ok, "forecaster": "TabPFN-v2 (CPU)"}


@app.get("/api/stations")
def stations():
    return {"stations": _model.stations}


@app.post("/api/forecast")
def forecast(inp: ForecastIn):
    feats = {c: getattr(inp, c) for c in FEATURES}
    fc = _model.predict(feats, inp.station)
    tip = advise(inp.plant, fc)
    return JSONResponse({
        "forecast": {
            "station": fc.station,
            "last_frost_date": fc.date_str,
            "last_frost_doy": fc.last_frost_doy,
            "range_low": fc.low_date,
            "range_high": fc.high_date,
            "days_from_now": fc.days_from_now,
        },
        "advice": tip,
        "plant": inp.plant,
    })


@app.get("/")
def index():
    return FileResponse(os.path.join(WEB, "index.html"))


# Serve frontend assets (scene.js, app.js) under /assets.
app.mount("/assets", StaticFiles(directory=os.path.join(WEB, "assets")), name="assets")
