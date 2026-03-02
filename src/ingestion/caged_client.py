from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import StringIO
import os
import re
import unicodedata

import numpy as np
import pandas as pd
import requests


@dataclass(frozen=True)
class CAGEDClient:
    """CAGED client with strict-real mode by default."""

    seed: int = 99
    use_real: bool = True
    allow_synthetic: bool = False
    timeout: int = 20

    def fetch_monthly(self, start: str = "2018-01", end: str = "2026-01") -> pd.DataFrame:
        if self.use_real:
            caged_csv_url = os.getenv("CAGED_AM_CSV_URL", "").strip()
            caged_xlsx_url = os.getenv("CAGED_AM_XLSX_URL", "").strip()
            try:
                if caged_csv_url:
                    df = self._fetch_real_csv(caged_csv_url)
                elif caged_xlsx_url:
                    df = self._fetch_real_xlsx(caged_xlsx_url)
                elif not self.allow_synthetic:
                    raise RuntimeError("CAGED requires env var CAGED_AM_CSV_URL or CAGED_AM_XLSX_URL.")
                else:
                    df = pd.DataFrame()
                if not df.empty:
                    mask = (df["year_month"] >= start) & (df["year_month"] <= end)
                    return df.loc[mask].reset_index(drop=True)
            except Exception as exc:
                if not self.allow_synthetic:
                    raise RuntimeError(f"CAGED ingestion failed: {exc}") from exc
        if self.allow_synthetic:
            return self._fetch_synthetic(start, end)
        raise RuntimeError("CAGED real ingestion unavailable and synthetic fallback is disabled.")

    def _fetch_real_csv(self, url: str) -> pd.DataFrame:
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        text = response.text
        df = pd.read_csv(StringIO(text))

        cols = {c.lower().strip(): c for c in df.columns}
        if "year_month" in cols and "am_net_jobs" in cols:
            out = df[[cols["year_month"], cols["am_net_jobs"]]].copy()
            out.columns = ["year_month", "am_net_jobs"]
            out["year_month"] = out["year_month"].astype(str).str.slice(0, 7)
            out["am_net_jobs"] = pd.to_numeric(out["am_net_jobs"], errors="coerce")
            return out.dropna().sort_values("year_month").reset_index(drop=True)
        raise ValueError("CAGED CSV must expose columns: year_month, am_net_jobs")

    def _fetch_real_xlsx(self, url: str) -> pd.DataFrame:
        sheets = pd.read_excel(url, sheet_name=None)
        if not isinstance(sheets, dict):
            sheets = {"sheet": sheets}

        for _, raw_df in sheets.items():
            parsed = self._parse_xlsx_sheet(raw_df)
            if not parsed.empty:
                return parsed
        raise ValueError("Unable to parse CAGED XLSX with Amazonas monthly net jobs.")

    def _parse_xlsx_sheet(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        if raw_df is None or raw_df.empty:
            return pd.DataFrame(columns=["year_month", "am_net_jobs"])

        df = raw_df.copy()
        df.columns = [self._norm(c) for c in df.columns]

        ym_col = self._find_col(df.columns, ("competencia", "periodo", "referencia", "ano_mes", "mes"))
        uf_col = self._find_col(df.columns, ("uf", "estado", "unidade_federacao"))
        saldo_col = self._find_col(df.columns, ("saldo",))
        adm_col = self._find_col(df.columns, ("admissoes", "admitidos", "admissoes_ajustadas"))
        des_col = self._find_col(df.columns, ("desligamentos", "desligados"))

        if ym_col is None:
            return pd.DataFrame(columns=["year_month", "am_net_jobs"])

        if uf_col is not None:
            uf_text = df[uf_col].astype(str).map(self._norm)
            df = df[(uf_text == "am") | (uf_text == "amazonas")].copy()

        if df.empty:
            return pd.DataFrame(columns=["year_month", "am_net_jobs"])

        df["year_month"] = df[ym_col].map(self._parse_year_month)
        df = df[df["year_month"].notna()].copy()
        if df.empty:
            return pd.DataFrame(columns=["year_month", "am_net_jobs"])

        if saldo_col is not None:
            df["am_net_jobs"] = pd.to_numeric(df[saldo_col], errors="coerce")
        elif adm_col is not None and des_col is not None:
            adm = pd.to_numeric(df[adm_col], errors="coerce")
            des = pd.to_numeric(df[des_col], errors="coerce")
            df["am_net_jobs"] = adm - des
        else:
            return pd.DataFrame(columns=["year_month", "am_net_jobs"])

        out = df[["year_month", "am_net_jobs"]].dropna()
        if out.empty:
            return pd.DataFrame(columns=["year_month", "am_net_jobs"])
        out = out.groupby("year_month", as_index=False)["am_net_jobs"].sum()
        return out.sort_values("year_month").reset_index(drop=True)

    def _norm(self, value) -> str:
        s = str(value).strip().lower()
        s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
        s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
        return s

    def _find_col(self, cols, keywords: tuple[str, ...]) -> str | None:
        for col in cols:
            if any(k in col for k in keywords):
                return col
        return None

    def _parse_year_month(self, value) -> str | None:
        if pd.isna(value):
            return None
        if isinstance(value, (datetime, pd.Timestamp)):
            return pd.Timestamp(value).strftime("%Y-%m")

        s = str(value).strip()
        if not s:
            return None

        if re.fullmatch(r"\d{6}", s):
            return f"{s[:4]}-{s[4:]}"
        if re.fullmatch(r"\d{4}-\d{2}", s):
            return s
        if re.fullmatch(r"\d{2}/\d{4}", s):
            mm, yyyy = s.split("/")
            return f"{yyyy}-{mm}"

        month_map = {
            "jan": "01",
            "fev": "02",
            "mar": "03",
            "abr": "04",
            "mai": "05",
            "jun": "06",
            "jul": "07",
            "ago": "08",
            "set": "09",
            "out": "10",
            "nov": "11",
            "dez": "12",
        }
        norm = self._norm(s)
        m = re.fullmatch(r"([a-z]{3})_(\d{4})", norm)
        if m and m.group(1) in month_map:
            return f"{m.group(2)}-{month_map[m.group(1)]}"
        return None

    def _fetch_synthetic(self, start: str, end: str) -> pd.DataFrame:
        months = pd.period_range(start=start, end=end, freq="M").astype(str)
        rng = np.random.default_rng(self.seed)
        t = np.arange(len(months))
        am_net_jobs = 1200 + 30 * np.sin(t / 4) + 1.8 * t + rng.normal(0, 35, len(months))
        return pd.DataFrame({"year_month": months, "am_net_jobs": am_net_jobs.round(2)})
