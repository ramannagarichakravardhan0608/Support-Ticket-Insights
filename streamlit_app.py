from __future__ import annotations

import logging
from html import escape
from pathlib import Path

import streamlit as st

from app.data_loader import load_tickets
from app.query_engine import build_assistant
from app.llm import LLMError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
LOGGER = logging.getLogger(__name__)


st.set_page_config(
    page_title="Support Ticket Insights",
    page_icon="◼",
    layout="wide",
)


@st.cache_resource(show_spinner="Loading tickets and initializing assistant...")
def load_assistant():
    dataframe = load_tickets()
    return build_assistant(dataframe), dataframe


def render_sidebar() -> str:
    st.sidebar.markdown(
        """
        <div class="sidebar-shell">
            <div class="sidebar-kicker">Support Desk</div>
            <div class="sidebar-title">Ticket Intelligence</div>
            <div class="sidebar-copy">Ask natural-language questions and get structured answers from the ticket dataset.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.markdown('<div class="sidebar-section-title">Quick prompts</div>', unsafe_allow_html=True)
    examples = [
        "How many open tickets are there?",
        "Show high priority tickets.",
        "Which agent resolved the most tickets?",
        "List unresolved tickets.",
        "What are the common issues reported?",
    ]
    for example in examples:
        if st.sidebar.button(example, use_container_width=True, key=f"sb_{example}"):
            st.session_state["pending_question"] = example

    st.sidebar.markdown('<div class="sidebar-section-title">Data source</div>', unsafe_allow_html=True)
    st.sidebar.code(str(Path("support_tickets.xlsx").resolve()))
    return st.session_state.get("pending_question", st.session_state.get("question", ""))


def metric_tile(label: str, value: str, accent: str) -> str:
    return f"""
    <div class="metric-tile" style="border-top: 4px solid {accent};">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
    </div>
    """


def dataframe_summary_table(dataframe, column: str, title: str):
    if column not in dataframe.columns:
        return
    summary = dataframe[column].value_counts().rename_axis(column).reset_index(name="count")
    st.markdown(f'<div class="section-label">{title}</div>', unsafe_allow_html=True)
    st.markdown(render_html_table(summary, max_rows=25), unsafe_allow_html=True)


def render_html_table(dataframe, max_rows: int = 15) -> str:
    preview = dataframe.head(max_rows)
    headers = "".join(f"<th>{escape(str(column))}</th>" for column in preview.columns)
    rows = []
    for _, row in preview.iterrows():
        cells = "".join(f"<td>{escape(str(value))}</td>" for value in row.tolist())
        rows.append(f"<tr>{cells}</tr>")
    rows_html = "".join(rows) if rows else '<tr><td colspan="99">No rows found</td></tr>'
    return f"""
    <div class="table-shell">
        <div class="table-scroll">
            <table class="clean-table">
                <thead><tr>{headers}</tr></thead>
                <tbody>{rows_html}</tbody>
            </table>
        </div>
    </div>
    """


def main() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg: #f6f1e8;
            --panel: rgba(255, 255, 255, 0.88);
            --panel-strong: #ffffff;
            --ink: #172033;
            --muted: #5f6b7a;
            --line: rgba(23, 32, 51, 0.10);
            --gold: #b45309;
            --teal: #0f766e;
            --navy: #1d3557;
            --sand: #f2e6d8;
        }

        html, body, [class*="css"] {
            font-family: "Inter", "Segoe UI", "Helvetica Neue", sans-serif;
        }

        .stApp {
            background:
                radial-gradient(circle at 12% 0%, rgba(180, 83, 9, 0.12), transparent 28%),
                radial-gradient(circle at 88% 4%, rgba(15, 118, 110, 0.10), transparent 24%),
                linear-gradient(180deg, #fcfaf6 0%, #f6f1e8 100%);
            color: var(--ink);
        }

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #fdfaf5 0%, #f4efe7 100%);
            border-right: 1px solid rgba(23, 32, 51, 0.08);
        }

        section[data-testid="stSidebar"] * {
            color: var(--ink);
        }

        .block-container {
            padding-top: 1.55rem;
            padding-bottom: 2rem;
        }

        .hero {
            position: relative;
            padding: 1.7rem 1.8rem 1.6rem;
            border-radius: 1.55rem;
            background:
                linear-gradient(135deg, rgba(23, 32, 51, 0.98) 0%, rgba(29, 53, 87, 0.98) 58%, rgba(15, 118, 110, 0.96) 100%);
            color: white;
            box-shadow: 0 20px 48px rgba(23, 32, 51, 0.24);
            margin-bottom: 1.1rem;
            overflow: hidden;
        }

        .hero::before,
        .hero::after {
            content: "";
            position: absolute;
            border-radius: 50%;
            filter: blur(2px);
            opacity: 0.28;
        }

        .hero::before {
            width: 220px;
            height: 220px;
            right: -70px;
            top: -80px;
            background: rgba(242, 230, 216, 0.22);
        }

        .hero::after {
            width: 160px;
            height: 160px;
            right: 55px;
            bottom: -70px;
            background: rgba(180, 83, 9, 0.20);
        }

        .eyebrow {
            text-transform: uppercase;
            letter-spacing: 0.22em;
            font-size: 0.7rem;
            opacity: 0.8;
            margin-bottom: 0.55rem;
        }

        .hero h1 {
            margin: 0;
            font-size: 2.35rem;
            line-height: 1.03;
            font-family: "Georgia", "Times New Roman", serif;
        }

        .hero p {
            margin: 0.7rem 0 0;
            max-width: 58rem;
            font-size: 1rem;
            line-height: 1.55;
            color: rgba(255, 255, 255, 0.88);
        }

        .pill-row {
            display: flex;
            gap: 0.55rem;
            flex-wrap: wrap;
            margin-top: 1rem;
        }

        .pill {
            padding: 0.38rem 0.72rem;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.10);
            border: 1px solid rgba(255, 255, 255, 0.15);
            font-size: 0.82rem;
            color: rgba(255, 255, 255, 0.92);
        }

        .panel {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 1.35rem;
            box-shadow: 0 14px 34px rgba(23, 32, 51, 0.06);
            backdrop-filter: blur(12px);
            padding: 1.05rem 1.1rem 1.1rem;
        }

        .panel-title {
            font-family: "Georgia", "Times New Roman", serif;
            font-size: 1.2rem;
            margin-bottom: 0.35rem;
            color: var(--ink);
        }

        .panel-subtitle {
            color: var(--muted);
            font-size: 0.94rem;
            margin-bottom: 0.9rem;
        }

        .metric-tile {
            background: var(--panel-strong);
            border-radius: 1rem;
            border: 1px solid var(--line);
            padding: 0.95rem 1rem;
            box-shadow: 0 10px 22px rgba(23, 32, 51, 0.05);
        }

        .metric-label {
            color: var(--muted);
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 0.32rem;
        }

        .metric-value {
            font-family: "Georgia", "Times New Roman", serif;
            font-size: 1.45rem;
            color: var(--ink);
            line-height: 1.1;
        }

        .section-label {
            color: var(--ink);
            font-size: 0.92rem;
            font-weight: 700;
            margin: 0.35rem 0 0.55rem;
        }

        .sidebar-shell {
            padding: 1rem 0 0.25rem;
        }

        .sidebar-kicker {
            text-transform: uppercase;
            letter-spacing: 0.2em;
            font-size: 0.69rem;
            color: #c2410c;
            margin-bottom: 0.45rem;
        }

        .sidebar-title {
            font-family: "Georgia", "Times New Roman", serif;
            font-size: 1.62rem;
            line-height: 1.05;
            color: var(--ink);
            margin-bottom: 0.55rem;
        }

        .sidebar-copy {
            color: var(--muted);
            line-height: 1.5;
            margin-bottom: 1rem;
        }

        .sidebar-section-title {
            text-transform: uppercase;
            letter-spacing: 0.14em;
            font-size: 0.7rem;
            color: var(--teal);
            margin: 1rem 0 0.45rem;
            font-weight: 700;
        }

        section[data-testid="stSidebar"] button {
            background: #ffffff !important;
            color: var(--ink) !important;
            border: 1px solid rgba(23, 32, 51, 0.14) !important;
            border-radius: 0.95rem !important;
            padding: 0.75rem 0.9rem !important;
            box-shadow: 0 8px 18px rgba(23, 32, 51, 0.05) !important;
        }

        section[data-testid="stSidebar"] button:hover {
            background: #fff7ed !important;
            border-color: rgba(194, 65, 12, 0.35) !important;
            color: #111827 !important;
        }

        section[data-testid="stSidebar"] code {
            background: #1f2937 !important;
            color: #f8fafc !important;
            border-radius: 0.9rem !important;
            padding: 0.9rem !important;
            font-size: 0.8rem !important;
            white-space: pre-wrap !important;
            word-break: break-word !important;
        }

        button[kind="primary"] {
            background: linear-gradient(135deg, var(--gold), #d97706) !important;
            border: 0 !important;
            border-radius: 999px !important;
            box-shadow: 0 10px 22px rgba(180, 83, 9, 0.22) !important;
            color: white !important;
        }

        button[kind="primary"]:hover {
            filter: brightness(1.02);
        }

        .stTextInput input {
            border-radius: 999px !important;
            border: 1px solid rgba(23, 32, 51, 0.12) !important;
            padding: 0.92rem 1rem !important;
            background: rgba(255, 255, 255, 0.96) !important;
            color: var(--ink) !important;
        }

        .stTextInput input:focus {
            border-color: rgba(15, 118, 110, 0.45) !important;
            box-shadow: 0 0 0 0.2rem rgba(15, 118, 110, 0.12) !important;
        }

        div[data-testid="stDataFrame"] {
            border-radius: 1rem;
            overflow: hidden;
            border: 1px solid var(--line);
        }

        .stButton button {
            border-radius: 0.95rem !important;
        }

        .stButton > button {
            background: #fffaf3 !important;
            border: 1px solid rgba(194, 65, 12, 0.18) !important;
            color: var(--ink) !important;
            min-height: 3.4rem !important;
            line-height: 1.2 !important;
            box-shadow: 0 8px 18px rgba(23, 32, 51, 0.04) !important;
        }

        .stButton > button:hover {
            background: #fff1dd !important;
            border-color: rgba(194, 65, 12, 0.38) !important;
            color: #111827 !important;
        }

        .table-shell {
            width: 100%;
            overflow-x: auto;
            border: 1px solid var(--line);
            border-radius: 1rem;
            background: rgba(255, 255, 255, 0.92);
            box-shadow: 0 10px 22px rgba(23, 32, 51, 0.05);
        }

        .table-scroll {
            min-width: 100%;
        }

        .clean-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.93rem;
            color: var(--ink);
        }

        .clean-table thead th {
            position: sticky;
            top: 0;
            background: #f8fafc;
            text-align: left;
            padding: 0.8rem 0.9rem;
            border-bottom: 1px solid var(--line);
            white-space: nowrap;
        }

        .clean-table tbody td {
            padding: 0.8rem 0.9rem;
            border-bottom: 1px solid rgba(23, 32, 51, 0.07);
            vertical-align: top;
        }

        .clean-table tbody tr:nth-child(even) {
            background: rgba(245, 248, 252, 0.65);
        }

        .clean-table tbody tr:hover {
            background: rgba(255, 247, 237, 0.9);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="hero">
            <div class="eyebrow">Support Ticket Intelligence</div>
            <h1>Support Ticket Assistant</h1>
            <p>Search, filter, and summarize your support ticket workbook with natural language. Results are rendered as clean reports instead of raw debug text.</p>
            <div class="pill-row">
                <div class="pill">Natural language</div>
                <div class="pill">LLM structured planning</div>
                <div class="pill">Pandas analysis</div>
                <div class="pill">Readable output</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    assistant, dataframe = load_assistant()
    question = render_sidebar()
    if "pending_question" in st.session_state:
        st.session_state["question_input"] = st.session_state["pending_question"]
        st.session_state["question"] = st.session_state["pending_question"]
        question = st.session_state["pending_question"]
        del st.session_state["pending_question"]

    total_tickets = len(dataframe)
    open_tickets = int((dataframe["status"].astype(str).str.casefold() == "open").sum()) if "status" in dataframe.columns else 0
    resolved_tickets = int((dataframe["status"].astype(str).str.casefold() == "resolved").sum()) if "status" in dataframe.columns else 0
    high_priority = int((dataframe["priority"].astype(str).str.casefold() == "high").sum()) if "priority" in dataframe.columns else 0

    stat_cols = st.columns(4, gap="small")
    stat_payload = [
        ("Tickets", str(total_tickets), "#c2410c"),
        ("Open", str(open_tickets), "#0f766e"),
        ("Resolved", str(resolved_tickets), "#1d4ed8"),
        ("High priority", str(high_priority), "#7c2d12"),
    ]
    for column, (label, value, accent) in zip(stat_cols, stat_payload, strict=False):
        column.markdown(metric_tile(label, value, accent), unsafe_allow_html=True)

    st.write("")

    col_left, col_right = st.columns([1.35, 0.85], gap="large")

    with col_left:
        st.markdown(
            """
            <div class="panel">
                <div class="panel-title">Ask a question</div>
                <div class="panel-subtitle">Use plain language. The assistant converts your request into a structured operation and returns the answer in a clean report format.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.write("")

        question = st.text_input(
            "Question",
            value=question,
            placeholder="e.g. How many open tickets are there?",
            label_visibility="collapsed",
            key="question_input",
        )

        quick_cols = st.columns(3)
        quick_examples = [
            "How many open tickets are there?",
            "Show high priority tickets.",
            "Which agent resolved the most tickets?",
        ]
        for index, (col, example) in enumerate(zip(quick_cols, quick_examples, strict=False)):
            if col.button(example, use_container_width=True, key=f"quick_{index}"):
                st.session_state["pending_question"] = example
                st.rerun()

        run_clicked = st.button("Run query", type="primary", use_container_width=True)

        if run_clicked and question.strip():
            with st.spinner("Thinking..."):
                try:
                    answer = assistant.answer(question.strip())
                    with st.container(border=True):
                        st.markdown("#### Result")
                        st.caption("Ready to scan. Expand the table or read the summary below.")
                        st.markdown(answer)
                except LLMError as exc:
                    st.error(str(exc))
                except Exception as exc:  # noqa: BLE001
                    LOGGER.exception("Streamlit query failed")
                    st.error(f"Query failed: {exc}")

        st.write("")
        st.markdown(
            """
            <div class="panel">
                <div class="panel-title">Ticket sample</div>
                <div class="panel-subtitle">Preview of the first 15 rows from the workbook.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(render_html_table(dataframe, max_rows=15), unsafe_allow_html=True)

    with col_right:
        st.markdown(
            """
            <div class="panel">
                <div class="panel-title">Dataset summary</div>
                <div class="panel-subtitle">High-level breakdowns pulled directly from the workbook.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if "status" in dataframe.columns:
            dataframe_summary_table(dataframe, "status", "Status distribution")
        if "priority" in dataframe.columns:
            dataframe_summary_table(dataframe, "priority", "Priority distribution")
        if "category" in dataframe.columns:
            dataframe_summary_table(dataframe, "category", "Category distribution")


if __name__ == "__main__":
    main()
