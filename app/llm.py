from __future__ import annotations

import importlib
import logging
import re
from typing import Any

import requests

from app.utils import extract_json_object

LOGGER = logging.getLogger(__name__)


class LLMError(RuntimeError):
    pass


class HeuristicPlanner:
    def plan(self, question: str, columns: list[str]) -> dict[str, Any]:
        q = question.casefold()
        filters: dict[str, Any] = {}

        if any(token in q for token in ["how many", "count", "number of", "total"]):
            action = "count"
        elif "common issue" in q or "common issues" in q or "frequent issue" in q:
            action = "common_issues"
        elif "resolved the most" in q or "most tickets" in q and "agent" in q:
            action = "top_agent"
        elif "unresolved" in q or "open tickets" in q or "open ticket" in q:
            action = "unresolved" if "unresolved" in q else "filter"
            filters["status"] = "Open"
        else:
            action = "filter"

        if "high priority" in q:
            filters["priority"] = "High"
        elif "critical priority" in q:
            filters["priority"] = "Critical"
        elif "medium priority" in q:
            filters["priority"] = "Medium"
        elif "low priority" in q:
            filters["priority"] = "Low"

        if "resolved" in q and action in {"filter", "count"}:
            filters["status"] = "Resolved"
        elif "escalated" in q:
            filters["status"] = "Escalated"
        elif "open" in q and action in {"filter", "count"}:
            filters["status"] = "Open"

        category_match = re.search(r"\b(billing|technical|general)\b", q)
        if category_match:
            filters["category"] = category_match.group(1).capitalize()

        top_n_match = re.search(r"\btop (\d+)\b", q)
        top_n = int(top_n_match.group(1)) if top_n_match else 5

        plan: dict[str, Any] = {"action": action, "filters": filters, "top_n": top_n, "_source": "heuristic"}
        if action == "top_agent":
            plan["metric"] = "resolved"
        return plan


class HuggingFacePlanner:
    def __init__(self, api_key: str | None = None, model_name: str | None = None) -> None:
        self.api_key = api_key
        self.model_name = model_name

    def plan(self, question: str, columns: list[str]) -> dict[str, Any]:
        try:
            config = importlib.import_module("app.config")
            config = importlib.reload(config)
        except ModuleNotFoundError:
            LOGGER.info("app.config is not available, using heuristic planner.")
            return HeuristicPlanner().plan(question, columns)

        api_key = self.api_key or getattr(config, "HF_API_KEY", "")
        model_name = self.model_name or getattr(config, "MODEL_NAME", "")

        if not api_key or api_key == "PASTE_YOUR_HUGGINGFACE_API_KEY_HERE" or not model_name:
            LOGGER.info("Hugging Face config is incomplete, using heuristic planner.")
            return HeuristicPlanner().plan(question, columns)

        prompt = self._build_prompt(question, columns)
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 180,
                "temperature": 0.0,
                "return_full_text": False,
            },
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        endpoint = f"https://api-inference.huggingface.co/models/{model_name}"
        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            LOGGER.warning("Hugging Face unreachable, using heuristic fallback: %s", exc)
            return HeuristicPlanner().plan(question, columns)

        data = response.json()
        LOGGER.debug("HF response type: %s", type(data).__name__)

        if isinstance(data, dict) and data.get("error"):
            raise LLMError(str(data["error"]))

        if isinstance(data, list) and data:
            generated = data[0].get("generated_text", "")
        elif isinstance(data, dict):
            generated = data.get("generated_text", "")
        else:
            raise LLMError("Unexpected response format from Hugging Face.")

        if not generated:
            raise LLMError("Hugging Face returned an empty response.")

        try:
            plan = extract_json_object(generated)
            plan["_source"] = "huggingface"
            return plan
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"Failed to parse JSON plan: {exc}") from exc

    def _build_prompt(self, question: str, columns: list[str]) -> str:
        schema = ", ".join(columns)
        return f"""
You are a planner for a support ticket analytics API.
Convert the user's question into a single JSON object only.
Do not include markdown, code fences, explanations, or extra text.

Allowed actions:
- "count": count tickets after applying filters
- "filter": return matching tickets
- "unresolved": return unresolved tickets
- "top_agent": find the agent with the most resolved tickets
- "common_issues": summarize frequent issues

Available dataframe columns:
{schema}

Use this JSON shape:
{{
  "action": "count|filter|unresolved|top_agent|common_issues",
  "filters": {{
    "status": "Open|Resolved|Escalated",
    "priority": "Low|Medium|High|Critical",
    "category": "Billing|General|Technical",
    "agent_id": "AGT-01"
  }},
  "limit": 10,
  "top_n": 5,
  "metric": "resolved"
}}

Examples:
User: How many open tickets are there?
JSON: {{"action":"count","filters":{{"status":"Open"}}}}

User: Show high priority unresolved tickets
JSON: {{"action":"filter","filters":{{"priority":"High","status":"Open"}}}}

User: Which agent resolved the most tickets?
JSON: {{"action":"top_agent","metric":"resolved"}}

User question: {question}
JSON:
""".strip()
