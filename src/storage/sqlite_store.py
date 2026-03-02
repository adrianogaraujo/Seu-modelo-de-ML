from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Dict

import pandas as pd


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(db_path)


def init_db(db_path: Path) -> None:
    with closing(_connect(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS monthly_observations (
                year_month TEXT PRIMARY KEY,
                target_default_rate REAL NOT NULL,
                north_proxy REAL NOT NULL,
                am_unemployment_rate REAL NOT NULL,
                am_retail_index REAL NOT NULL,
                am_net_jobs REAL NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS historical_predictions (
                year_month TEXT PRIMARY KEY,
                target_default_rate REAL NOT NULL,
                y_hat REAL NOT NULL,
                residual REAL NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS model_metrics (
                run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                mae REAL NOT NULL,
                rmse REAL NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        conn.commit()


def upsert_monthly_observations(db_path: Path, df: pd.DataFrame) -> None:
    cols = [
        "year_month",
        "target_default_rate",
        "north_proxy",
        "am_unemployment_rate",
        "am_retail_index",
        "am_net_jobs",
    ]
    data = df[cols].to_dict(orient="records")
    with closing(_connect(db_path)) as conn:
        conn.executemany(
            """
            INSERT INTO monthly_observations (
                year_month, target_default_rate, north_proxy,
                am_unemployment_rate, am_retail_index, am_net_jobs
            ) VALUES (
                :year_month, :target_default_rate, :north_proxy,
                :am_unemployment_rate, :am_retail_index, :am_net_jobs
            )
            ON CONFLICT(year_month) DO UPDATE SET
                target_default_rate=excluded.target_default_rate,
                north_proxy=excluded.north_proxy,
                am_unemployment_rate=excluded.am_unemployment_rate,
                am_retail_index=excluded.am_retail_index,
                am_net_jobs=excluded.am_net_jobs
            """,
            data,
        )
        conn.commit()


def upsert_historical_predictions(db_path: Path, df: pd.DataFrame) -> None:
    data = df[["year_month", "target_default_rate", "y_hat", "residual"]].to_dict(orient="records")
    with closing(_connect(db_path)) as conn:
        conn.executemany(
            """
            INSERT INTO historical_predictions (year_month, target_default_rate, y_hat, residual)
            VALUES (:year_month, :target_default_rate, :y_hat, :residual)
            ON CONFLICT(year_month) DO UPDATE SET
                target_default_rate=excluded.target_default_rate,
                y_hat=excluded.y_hat,
                residual=excluded.residual
            """,
            data,
        )
        conn.commit()


def insert_metrics(db_path: Path, metrics: Dict[str, float]) -> None:
    with closing(_connect(db_path)) as conn:
        conn.execute(
            """
            INSERT INTO model_metrics (mae, rmse, payload_json)
            VALUES (?, ?, ?)
            """,
            (float(metrics["mae"]), float(metrics["rmse"]), json.dumps(metrics)),
        )
        conn.commit()


def fetch_historical_predictions(db_path: Path, from_month: str, to_month: str) -> pd.DataFrame:
    query = """
    SELECT year_month, target_default_rate, y_hat
    FROM historical_predictions
    WHERE year_month >= ? AND year_month <= ?
    ORDER BY year_month
    """
    with closing(_connect(db_path)) as conn:
        return pd.read_sql_query(query, conn, params=(from_month, to_month))
