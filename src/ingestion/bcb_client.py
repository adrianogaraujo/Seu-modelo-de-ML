from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import os

import numpy as np
import pandas as pd
import requests


@dataclass(frozen=True)
class BCBClient:
    """BCB client with strict-real mode by default."""

    seed: int = 42
    use_real: bool = True
    allow_synthetic: bool = False
    timeout: int = 20

    def fetch_monthly(self, start: str = "2018-01", end: str = "2026-01") -> pd.DataFrame:
        if self.use_real:
            target_code = os.getenv("BCB_TARGET_SERIES_CODE", "").strip()
            proxy_code = os.getenv("BCB_NORTH_PROXY_SERIES_CODE", "").strip()
            if target_code and proxy_code:
                try:
                    target_df = self._fetch_series(target_code, start, end).rename(
                        columns={"value": "target_default_rate"}
                    )
                    proxy_df = self._fetch_series(proxy_code, start, end).rename(
                        columns={"value": "north_proxy"}
                    )
                    merged = target_df.merge(proxy_df, on="year_month", how="inner")
                    if not merged.empty:
                        return merged.sort_values("year_month").reset_index(drop=True)
                except Exception as exc:
                    if not self.allow_synthetic:
                        raise RuntimeError(f"BCB ingestion failed: {exc}") from exc
            elif not self.allow_synthetic:
                raise RuntimeError(
                    "BCB requires env vars BCB_TARGET_SERIES_CODE and BCB_NORTH_PROXY_SERIES_CODE."
                )
        if self.allow_synthetic:
            return self._fetch_synthetic(start, end)
        raise RuntimeError("BCB real ingestion unavailable and synthetic fallback is disabled.")

    def _fetch_series(self, code: str, start: str, end: str) -> pd.DataFrame:
        start_date = datetime.strptime(f"{start}-01", "%Y-%m-%d").strftime("%d/%m/%Y")
        end_date = datetime.strptime(f"{end}-01", "%Y-%m-%d").strftime("%d/%m/%Y")
        url = (
            f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"
            f"?formato=json&dataInicial={start_date}&dataFinal={end_date}"
        )
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list) or not payload:
            raise ValueError("Empty BCB payload")

        rows = []
        for item in payload:
            raw_date = str(item.get("data", "")).strip()
            raw_value = str(item.get("valor", "")).replace(",", ".").strip()
            if not raw_date or not raw_value:
                continue
            dt = datetime.strptime(raw_date, "%d/%m/%Y")
            rows.append({"year_month": dt.strftime("%Y-%m"), "value": float(raw_value)})
        if not rows:
            raise ValueError("No rows parsed from BCB payload")

        df = pd.DataFrame(rows)
        return df.groupby("year_month", as_index=False)["value"].mean()

    def _fetch_synthetic(self, start: str, end: str) -> pd.DataFrame:
        months = pd.period_range(start=start, end=end, freq="M").astype(str)
        rng = np.random.default_rng(self.seed)
        t = np.arange(len(months))
        north_proxy = 7.0 + 0.5 * np.sin(t / 6) + rng.normal(0, 0.1, len(months))
        target_default_rate = 4.0 + 0.4 * north_proxy + rng.normal(0, 0.08, len(months))
        return pd.DataFrame(
            {
                "year_month": months,
                "north_proxy": north_proxy.round(4),
                "target_default_rate": target_default_rate.round(4),
            }
        )
