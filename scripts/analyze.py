"""Find a real, cited insight in the frost data using TabPFN-v2 feature analysis.

Questions:
  1. Which feature moves the last-frost date most? (latitude vs elevation vs winter temps)
  2. How much does the ENSO (La Nina / El Nino) signal shift frost, and does it hit cold
     northern stations differently than warm southern ones?
  3. Elevation vs latitude: past a certain latitude, which dominates?

All numbers printed here are real and reproducible from data/frost_history.csv.
"""
import os
import numpy as np
import pandas as pd

os.environ.setdefault("TABPFN_NO_BROWSER", "1")
from tabpfn import TabPFNRegressor
from tabpfn.constants import ModelVersion

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "frost_history.csv")
FEATURES = ["latitude", "elevation_m", "feb_mean_c", "mar_mean_c", "winter_min_c", "enso_index"]

df = pd.read_csv(DATA)
X = df[FEATURES].to_numpy()
y = df["last_frost_doy"].to_numpy()

reg = TabPFNRegressor.create_default_for_version(ModelVersion.V2, device="cpu")
reg.fit(X, y)

base = df[FEATURES].mean()

def predict_row(overrides):
    row = base.copy()
    for k, v in overrides.items():
        row[k] = v
    return float(reg.predict(row.to_numpy().reshape(1, -1))[0])

print("=== 1. Sensitivity: how many DAYS does the frost move per realistic swing? ===")
# Use the real 10th->90th percentile swing of each feature so comparisons are fair.
swings = {}
for f in FEATURES:
    lo, hi = np.percentile(df[f], 10), np.percentile(df[f], 90)
    d_lo = predict_row({f: lo})
    d_hi = predict_row({f: hi})
    swings[f] = (hi - lo, d_lo, d_hi, d_hi - d_lo)
    print(f"  {f:14s}: 10-90% range {lo:7.2f} -> {hi:7.2f}  moves frost by {d_hi - d_lo:+6.1f} days")

ranked = sorted(swings.items(), key=lambda kv: abs(kv[1][3]), reverse=True)
print("\n  Ranked by impact (biggest mover first):")
for f, (_, _, _, dd) in ranked:
    print(f"    {f:14s} {abs(dd):5.1f} days")

print("\n=== 2. ENSO (La Nina / El Nino) effect, north vs south ===")
# cold northern station (Fargo-like) vs warm southern (Houston-like)
north = dict(latitude=46.88, elevation_m=274, feb_mean_c=-9, mar_mean_c=-2, winter_min_c=-27)
south = dict(latitude=29.76, elevation_m=25, feb_mean_c=13, mar_mean_c=17, winter_min_c=-1)
for name, loc in [("north (Fargo-like)", north), ("south (Houston-like)", south)]:
    lanina = predict_row({**loc, "enso_index": -1.5})
    elnino = predict_row({**loc, "enso_index": 1.5})
    print(f"  {name:22s}: La Nina {lanina:6.1f}  El Nino {elnino:6.1f}  swing {elnino - lanina:+5.1f} days")

print("\n=== 3. Elevation vs latitude at a fixed mid-latitude ===")
# At ~40N, compare sea level vs 1600m (Denver), holding temps at their means
for elev in [50, 800, 1600]:
    d = predict_row({"latitude": 40.0, "elevation_m": elev})
    print(f"  40N, {elev:5d} m -> last frost DOY {d:6.1f}")

print("\n(reproduce: python scripts/analyze.py)")
