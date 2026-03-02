from __future__ import annotations

import os
import sys
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.ingestion.bcb_client import BCBClient  # noqa: E402
from src.ingestion.caged_client import CAGEDClient  # noqa: E402
from src.ingestion.sidra_client import SIDRAClient  # noqa: E402


class IngestionClientsTest(unittest.TestCase):
    def test_bcb_strict_mode_without_codes_fails(self):
        os.environ.pop("BCB_TARGET_SERIES_CODE", None)
        os.environ.pop("BCB_NORTH_PROXY_SERIES_CODE", None)
        with self.assertRaises(RuntimeError):
            BCBClient(use_real=True, allow_synthetic=False).fetch_monthly("2025-01", "2025-03")

    def test_bcb_fallback_allowed_when_explicit(self):
        os.environ.pop("BCB_TARGET_SERIES_CODE", None)
        os.environ.pop("BCB_NORTH_PROXY_SERIES_CODE", None)
        df = BCBClient(use_real=True, allow_synthetic=True).fetch_monthly("2025-01", "2025-03")
        self.assertEqual(list(df.columns), ["year_month", "north_proxy", "target_default_rate"])
        self.assertEqual(len(df), 3)

    def test_bcb_real_path_with_mocked_series(self):
        with patch.dict(
            os.environ,
            {"BCB_TARGET_SERIES_CODE": "1", "BCB_NORTH_PROXY_SERIES_CODE": "2"},
            clear=False,
        ):
            with patch.object(BCBClient, "_fetch_series") as mock_fetch:
                mock_fetch.side_effect = [
                    pd.DataFrame({"year_month": ["2025-01", "2025-02"], "value": [5.1, 5.2]}),
                    pd.DataFrame({"year_month": ["2025-01", "2025-02"], "value": [7.1, 7.0]}),
                ]
                out = BCBClient(use_real=True).fetch_monthly("2025-01", "2025-02")
                self.assertEqual(len(out), 2)
                self.assertIn("target_default_rate", out.columns)
                self.assertIn("north_proxy", out.columns)

    def test_sidra_parser_real_payload(self):
        payload = [
            {"NC": "Nível Territorial"},
            {"D3C": "202501", "V": "123,4"},
            {"D3C": "202502", "V": "125,0"},
        ]
        mock_resp = Mock()
        mock_resp.json.return_value = payload
        mock_resp.raise_for_status.return_value = None
        with patch("src.ingestion.sidra_client.requests.get", return_value=mock_resp):
            df = SIDRAClient(use_real=True)._fetch_real("http://fake")
            self.assertEqual(len(df), 2)
            self.assertIn("am_retail_index", df.columns)
            self.assertIn("am_unemployment_rate", df.columns)

    def test_caged_real_csv_contract(self):
        csv_content = "year_month,am_net_jobs\n2025-01,100\n2025-02,120\n"
        mock_resp = Mock()
        mock_resp.text = csv_content
        mock_resp.raise_for_status.return_value = None
        with patch("src.ingestion.caged_client.requests.get", return_value=mock_resp):
            df = CAGEDClient(use_real=True)._fetch_real_csv("http://fake")
            self.assertEqual(len(df), 2)
            self.assertEqual(df.iloc[0]["year_month"], "2025-01")

    def test_caged_real_xlsx_parses_saldo_for_am(self):
        sheet_df = pd.DataFrame(
            {
                "UF": ["Amazonas", "Sao Paulo"],
                "Competencia": ["2025-01", "2025-01"],
                "Saldo": [150, 999],
            }
        )
        with patch("src.ingestion.caged_client.pd.read_excel", return_value={"Base": sheet_df}):
            df = CAGEDClient(use_real=True)._fetch_real_xlsx("http://fake")
            self.assertEqual(len(df), 1)
            self.assertEqual(df.iloc[0]["year_month"], "2025-01")
            self.assertEqual(float(df.iloc[0]["am_net_jobs"]), 150.0)

    def test_caged_real_xlsx_parses_adm_minus_deslig(self):
        sheet_df = pd.DataFrame(
            {
                "Estado": ["AM", "AM"],
                "Mes": ["jan/2025", "fev/2025"],
                "Admissoes": [300, 320],
                "Desligamentos": [280, 330],
            }
        )
        with patch("src.ingestion.caged_client.pd.read_excel", return_value={"Painel": sheet_df}):
            df = CAGEDClient(use_real=True)._fetch_real_xlsx("http://fake")
            self.assertEqual(len(df), 2)
            self.assertEqual(float(df.iloc[0]["am_net_jobs"]), 20.0)
            self.assertEqual(float(df.iloc[1]["am_net_jobs"]), -10.0)


if __name__ == "__main__":
    unittest.main()
