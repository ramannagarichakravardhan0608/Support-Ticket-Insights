from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

LOGGER = logging.getLogger(__name__)


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_tickets(file_name: str = "support_tickets.xlsx") -> pd.DataFrame:
    path = _project_root() / file_name
    if not path.exists():
        candidates = sorted(_project_root().glob("*.xlsx"))
        if len(candidates) == 1:
            path = candidates[0]
        else:
            raise FileNotFoundError(
                f"Could not find {file_name}. Available xlsx files: {[p.name for p in candidates]}"
            )

    LOGGER.info("Loading support tickets from %s", path)
    df = pd.read_excel(path)
    df = _normalize_dataframe(df)
    LOGGER.info("Loaded %d ticket rows with columns: %s", len(df), list(df.columns))
    return df


def _normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()

    result.columns = [str(col).strip() for col in result.columns]
    for column in result.columns:
        if result[column].dtype == "object":
            result.loc[:, column] = (
                result[column]
                .astype("string")
                .fillna("")
                .replace({"nan": "", "NaT": ""})
            )

    if "created_at" in result.columns:
        result.loc[:, "created_at"] = pd.to_datetime(result["created_at"], errors="coerce")
    if "customer_rating" in result.columns:
        result.loc[:, "customer_rating"] = pd.to_numeric(result["customer_rating"], errors="coerce")
    for col in ("response_time_hrs", "resolution_time_hrs"):
        if col in result.columns:
            result.loc[:, col] = pd.to_numeric(result[col], errors="coerce")

    return result
