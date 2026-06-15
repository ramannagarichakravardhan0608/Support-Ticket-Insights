from __future__ import annotations

import json
import re
from typing import Any

import pandas as pd


JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def normalize_text(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def normalize_lookup(value: Any) -> str:
    return normalize_text(value).casefold()


def extract_json_object(text: str) -> dict[str, Any]:
    candidate = text.strip()
    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    match = JSON_OBJECT_RE.search(candidate)
    if not match:
        raise ValueError("No JSON object found in LLM response.")

    parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("LLM response JSON must be an object.")
    return parsed


def dataframe_preview(df: pd.DataFrame, limit: int = 10) -> str:
    if df.empty:
        return "No matching tickets found."

    rows = []
    for _, row in df.head(limit).iterrows():
        parts = [
            f"ticket_id={normalize_text(row.get('ticket_id'))}",
            f"status={normalize_text(row.get('status'))}",
            f"priority={normalize_text(row.get('priority'))}",
            f"agent_id={normalize_text(row.get('agent_id'))}",
            f"issue_summary={normalize_text(row.get('issue_summary'))}",
        ]
        rows.append("; ".join(parts))
    suffix = "" if len(df) <= limit else f" Showing first {limit} of {len(df)} tickets."
    return "\n".join(rows) + suffix


def format_number(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, (int,)):
        return str(value)
    return str(value)

