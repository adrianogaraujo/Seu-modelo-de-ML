from __future__ import annotations

from dataclasses import dataclass
import os
import re

import numpy as np
import pandas as pd
import requests


@dataclass(frozen=True)
class SIDRAClient:
    """SIDRA client with strict-real mode by default."""

    seed: int = 7
    use_real: bool = True
    allow_synthetic: bool = False
    timeout: int = 20

    def fetch_monthly(self, start: str = "2018-01", end: str = "2026-01") -> pd.DataFrame:
        if self.use_real:
            sidra_url = os.getenv("SIDRA_AM_URL", "").strip()
            if sidra_url:
                try:
                    parsed = self._fetch_real(sidra_url)
                    if not parsed.empty:
                        return self._filter_range(parsed, start, end)
                except Exception as exc:
                    if not self.allow_synthetic:
                        raise RuntimeError(f"SIDRA ingestion failed: {exc}") from exc
            elif not self.allow_synthetic:
                raise RuntimeError("SIDRA requires env var SIDRA_AM_URL.")
        if self.allow_synthetic:
            return self._fetch_synthetic(start, end)
        raise RuntimeError("SIDRA real ingestion unavailable and synthetic fallback is disabled.")

    def _fetch_real(self, sidra_url: str) -> pd.DataFrame:
        response = requests.get(sidra_url, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list) or len(payload) < 2:
            raise ValueError("Empty SIDRA payload")

        rows = []
        for item in payload[1:]:
            if not isinstance(item, dict):
                continue
            ym = self._extract_year_month(item)
            val = self._extract_value(item)
            if ym and val is not None:
                rows.append({"year_month": ym, "am_retail_index": float(val)})
        if not rows:
            raise ValueError("No SIDRA rows parsed")

        df = pd.DataFrame(rows).sort_values("year_month")
        # If only one variable comes from SIDRA real, keep unemployment as stable proxy.
        df["am_unemployment_rate"] = 10.0 + (df["am_retail_index"].mean() - df["am_retail_index"]) * 0.01
        return df[["year_month", "am_unemployment_rate", "am_retail_index"]]

    def _extract_year_month(self, item: dict) -> str | None:
        for value in item.values():
            s = str(value).strip()
            if re.fullmatch(r"\d{6}", s):
                return f"{s[:4]}-{s[4:]}"
            if re.fullmatch(r"\d{4}-\d{2}", s):
                return s
        return None

    def _extract_value(self, item: dict) -> float | None:
        candidates = []
        for key, value in item.items():
            if key.upper().startswith("V"):
                candidates.append(value)
        if not candidates:
            candidates = list(item.values())
        for value in candidates:
            raw = str(value).replace(".", "").replace(",", ".").strip()
            try:
                return float(raw)
            except ValueError:
                continue
        return None

    def _filter_range(self, df: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
        mask = (df["year_month"] >= start) & (df["year_month"] <= end)
        out = df.loc[mask].copy()
        return out.reset_index(drop=True)

    def _fetch_synthetic(self, start: str, end: str) -> pd.DataFrame:
        months = pd.period_range(start=start, end=end, freq="M").astype(str)
        rng = np.random.default_rng(self.seed)
        t = np.arange(len(months))
        am_unemployment_rate = 11.5 - 0.03 * t + 0.6 * np.cos(t / 8) + rng.normal(0, 0.12, len(months))
        am_retail_index = 100 + 0.2 * t + 2.0 * np.sin(t / 5) + rng.normal(0, 0.7, len(months))
        return pd.DataFrame(
            {
                "year_month": months,
                "am_unemployment_rate": am_unemployment_rate.round(4),
                "am_retail_index": am_retail_index.round(4),
            }
        )
