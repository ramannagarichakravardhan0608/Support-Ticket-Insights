from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

import pandas as pd

from app.llm import HuggingFacePlanner, LLMError
from app.utils import format_number, normalize_lookup, normalize_text

LOGGER = logging.getLogger(__name__)
AGENT_PATTERN = re.compile(r"^AGT-\d+$", re.IGNORECASE)


def _apply_filters(df: pd.DataFrame, filters: dict[str, Any] | None) -> pd.DataFrame:
    if not filters:
        return df

    result = df.copy()
    for key, value in filters.items():
        if value in (None, ""):
            continue
        if key not in result.columns:
            continue

        if key in {"status", "priority", "category", "agent_id", "ticket_id"}:
            mask = result[key].astype(str).map(normalize_lookup) == normalize_lookup(value)
            result = result.loc[mask]
        elif key == "issue_summary":
            mask = result[key].astype(str).str.contains(str(value), case=False, na=False)
            result = result.loc[mask]
        elif key in {"date_from", "date_to"} and "created_at" in result.columns:
            created = pd.to_datetime(result["created_at"], errors="coerce")
            if key == "date_from":
                result = result.loc[created >= pd.to_datetime(value)]
            else:
                result = result.loc[created <= pd.to_datetime(value)]

    return result


def count_tickets(df: pd.DataFrame, filters: dict[str, Any] | None = None) -> int:
    return int(len(_apply_filters(df, filters)))


def filter_tickets(df: pd.DataFrame, filters: dict[str, Any] | None = None) -> pd.DataFrame:
    return _apply_filters(df, filters)


def unresolved_tickets(df: pd.DataFrame) -> pd.DataFrame:
    if "status" not in df.columns:
        return df.iloc[0:0]
    status = df["status"].astype(str).map(normalize_lookup)
    return df.loc[status.isin({"open", "escalated"})]


def top_agent(df: pd.DataFrame, filters: dict[str, Any] | None = None) -> dict[str, Any]:
    working = _apply_filters(df, filters)
    if "status" in working.columns:
        working = working.loc[working["status"].astype(str).map(normalize_lookup) == "resolved"]
    if "agent_id" not in working.columns:
        raise ValueError("The dataframe does not contain an agent_id column.")

    agents = working["agent_id"].astype(str).str.strip()
    agents = agents[agents.str.match(r"^AGT-\d+$", na=False)]
    if agents.empty:
        raise ValueError("No valid agent identifiers were found in the data.")

    counts = agents.value_counts()
    agent = counts.index[0]
    return {"agent_id": agent, "resolved_tickets": int(counts.iloc[0])}


def common_issues(df: pd.DataFrame, filters: dict[str, Any] | None = None, top_n: int = 5) -> list[dict[str, Any]]:
    working = _apply_filters(df, filters)
    if "issue_summary" not in working.columns:
        raise ValueError("The dataframe does not contain an issue_summary column.")

    issues = working["issue_summary"].astype(str).map(normalize_text)
    issues = issues[issues != ""]
    if issues.empty:
        return []

    counts = issues.value_counts().head(top_n)
    return [
        {"issue_summary": issue, "count": int(count)}
        for issue, count in counts.items()
    ]


@dataclass
class TicketAssistant:
    df: pd.DataFrame
    planner: HuggingFacePlanner

    def answer(self, question: str) -> str:
        LOGGER.info("Processing query: %s", question)
        plan = self.planner.plan(question, list(self.df.columns))
        action = str(plan.get("action", "")).strip()
        filters = plan.get("filters") if isinstance(plan.get("filters"), dict) else None
        source = str(plan.get("_source", "")).strip()
        note = "Offline fallback used." if source == "heuristic" else ""

        if action == "count":
            total = count_tickets(self.df, filters)
            title = self._count_title(filters)
            return self._compose_report(
                title="Ticket count",
                note=note,
                body=f"**{title}:** {format_number(total)}",
                filters=filters,
            )

        if action == "filter":
            filtered = filter_tickets(self.df, filters)
            return self._compose_ticket_list(
                title="Matching tickets",
                df=filtered,
                note=note,
                filters=filters,
            )

        if action == "unresolved":
            filtered = unresolved_tickets(self.df)
            return self._compose_ticket_list(
                title="Unresolved tickets",
                df=filtered,
                note=note,
                filters=filters,
            )

        if action == "top_agent":
            result = top_agent(self.df, filters)
            body = (
                f"**Top agent:** {result['agent_id']}\n\n"
                f"**Resolved tickets:** {format_number(result['resolved_tickets'])}"
            )
            return self._compose_report(
                title="Top resolving agent",
                note=note,
                body=body,
                filters=filters,
            )

        if action == "common_issues":
            top_n = int(plan.get("top_n", 5) or 5)
            issues = common_issues(self.df, filters, top_n=top_n)
            if not issues:
                return self._compose_report(
                    title="Common issues",
                    note=note,
                    body="No issue summaries were found.",
                    filters=filters,
                )
            lines = "\n".join(
                f"{index}. {item['issue_summary']} ({format_number(item['count'])})"
                for index, item in enumerate(issues, start=1)
            )
            return self._compose_report(
                title="Common issues",
                note=note,
                body=lines,
                filters=filters,
            )

        raise ValueError(f"Unsupported action returned by the LLM: {action}")

    def _count_title(self, filters: dict[str, Any] | None) -> str:
        if not filters:
            return "All tickets"
        pieces = []
        for key, value in filters.items():
            if value in (None, ""):
                continue
            pieces.append(f"{key}={value}")
        return "Tickets matching " + ", ".join(pieces) if pieces else "All tickets"

    def _compose_report(
        self,
        title: str,
        body: str,
        note: str = "",
        filters: dict[str, Any] | None = None,
    ) -> str:
        parts = [f"### {title}"]
        if note:
            parts.append(f"> {note}")
        if filters:
            parts.append("**Filters applied:** " + self._filters_text(filters))
        parts.append(body)
        return "\n\n".join(parts)

    def _compose_ticket_list(
        self,
        title: str,
        df: pd.DataFrame,
        note: str = "",
        filters: dict[str, Any] | None = None,
    ) -> str:
        if df.empty:
            return self._compose_report(
                title=title,
                note=note,
                body="No matching tickets were found.",
                filters=filters,
            )

        columns = [col for col in ["ticket_id", "priority", "status", "agent_id", "issue_summary"] if col in df.columns]
        table = self._markdown_table(df[columns].head(10), columns)
        body = f"**Total tickets:** {format_number(len(df))}\n\n{table}"
        return self._compose_report(title=title, note=note, body=body, filters=filters)

    def _filters_text(self, filters: dict[str, Any]) -> str:
        pairs = [f"{key}={value}" for key, value in filters.items() if value not in (None, "")]
        return ", ".join(pairs) if pairs else "None"

    def _markdown_table(self, df: pd.DataFrame, columns: list[str]) -> str:
        headers = [self._pretty_column_name(column) for column in columns]
        rows = []
        for _, row in df.iterrows():
            cells = [self._sanitize_markdown(row.get(column)) for column in columns]
            rows.append("| " + " | ".join(cells) + " |")
        header_row = "| " + " | ".join(headers) + " |"
        separator = "| " + " | ".join(["---"] * len(headers)) + " |"
        return "\n".join([header_row, separator, *rows])

    def _pretty_column_name(self, name: str) -> str:
        return name.replace("_", " ").title()

    def _sanitize_markdown(self, value: Any) -> str:
        text = str(value) if value is not None else ""
        return text.replace("|", "\\|").replace("\n", " ").strip()


def build_assistant(df: pd.DataFrame) -> TicketAssistant:
    return TicketAssistant(df=df, planner=HuggingFacePlanner())
