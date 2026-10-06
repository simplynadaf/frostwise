"""FrostWise forecasting core: TabPFN-v2 (open weights) on CPU.

Predicts the last-spring-frost day-of-year from station climate features, and converts
that into the dates and the "days from now" a gardener actually cares about. 100% local:
once the v2 weights are cached, this runs with no network.
"""
from __future__ import annotations
import os
import datetime as dt
from dataclasses import dataclass

import numpy as np
import pandas as pd

os.environ.setdefault("TABPFN_NO_BROWSER", "1")

from tabpfn import TabPFNRegressor
from tabpfn.constants import ModelVersion

FEATURES = ["latitude", "elevation_m", "feb_mean_c", "mar_mean_c", "winter_min_c", "enso_index"]
DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "frost_history.csv")


@dataclass
class Forecast:
    last_frost_doy: int
    low_doy: int
    high_doy: int
    date_str: str
    low_date: str
    high_date: str
    days_from_now: int
    station: str


class FrostModel:
    """Loads data once, fits TabPFN-v2 once, serves instant predictions."""

    def __init__(self, csv_path: str = DATA):
        self.df = pd.read_csv(csv_path)
        self.stations = (
            self.df.groupby("station")[FEATURES].mean().reset_index()
            .sort_values("latitude").to_dict("records")
        )
        self._reg: TabPFNRegressor | None = None

    def _ensure_model(self):
        if self._reg is None:
            reg = TabPFNRegressor.create_default_for_version(ModelVersion.V2, device="cpu")
            reg.fit(self.df[FEATURES].to_numpy(), self.df["last_frost_doy"].to_numpy())
            self._reg = reg
        return self._reg

    @staticmethod
    def _doy_to_date(doy: int, year: int | None = None) -> dt.date:
        year = year or dt.date.today().year
        doy = max(1, min(366, int(doy)))
        return dt.date(year, 1, 1) + dt.timedelta(days=doy - 1)

    def predict(self, features: dict, station_label: str = "your location") -> Forecast:
        reg = self._ensure_model()
        x = np.array([[features[c] for c in FEATURES]], dtype=float)
        # Point prediction plus a calibrated interval from TabPFN's output quantiles.
        mean = float(reg.predict(x)[0])
        try:
            q = reg.predict(x, output_type="quantiles", quantiles=[0.1, 0.9])
            low, high = float(q[0][0]), float(q[1][0])
        except Exception:
            low, high = mean - 7, mean + 7

        doy = int(round(mean))
        today = dt.date.today()
        date = self._doy_to_date(doy, today.year)
        if date < today:  # last frost already passed this year -> show next year
            date = self._doy_to_date(doy, today.year + 1)
        return Forecast(
            last_frost_doy=doy,
            low_doy=int(round(low)),
            high_doy=int(round(high)),
            date_str=date.strftime("%B %d"),
            low_date=self._doy_to_date(int(round(low)), date.year).strftime("%b %d"),
            high_date=self._doy_to_date(int(round(high)), date.year).strftime("%b %d"),
            days_from_now=(date - today).days,
            station=station_label,
        )


if __name__ == "__main__":
    m = FrostModel()
    # Chicago-like inputs
    f = m.predict(dict(latitude=41.88, elevation_m=181, feb_mean_c=-2, mar_mean_c=4,
                       winter_min_c=-16, enso_index=0.0), "Chicago, IL")
    print(f)
