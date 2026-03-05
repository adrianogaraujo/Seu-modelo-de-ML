from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import os

import pandas as pd
import requests


@dataclass(frozen=True)
class BCBClient:
    """BCB client with strict-real mode by default."""

    use_real: bool = True
    timeout: int = 20

    def fetch_monthly(self, start: str = "2018-01", end: str = "2026-01") -> pd.DataFrame:
        if not self.use_real:
            raise RuntimeError("BCB supports only real ingestion.")

        target_code = os.getenv("BCB_TARGET_SERIES_CODE", "").strip()
        proxy_code = os.getenv("BCB_NORTH_PROXY_SERIES_CODE", "").strip()
        if not target_code or not proxy_code:
            raise RuntimeError(
                "BCB missing configuration: set BCB_TARGET_SERIES_CODE and BCB_NORTH_PROXY_SERIES_CODE."
            )

        try:
            target_df = self._fetch_series(target_code, start, end).rename(
                columns={"value": "target_default_rate"}
            )
            proxy_df = self._fetch_series(proxy_code, start, end).rename(
                columns={"value": "north_proxy"}
            )
        except requests.RequestException as exc:
            raise RuntimeError(f"BCB upstream fetch failed: {exc}") from exc
        except Exception as exc:
            raise RuntimeError(f"BCB parse failed: {exc}") from exc

        merged = target_df.merge(proxy_df, on="year_month", how="inner")
        if merged.empty:
            raise RuntimeError(f"BCB no rows in requested range: {start}..{end}.")
        return merged.sort_values("year_month").reset_index(drop=True)

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
