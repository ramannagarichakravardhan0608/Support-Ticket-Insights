from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.data_loader import load_tickets
from app.query_engine import build_assistant
from app.llm import LLMError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
LOGGER = logging.getLogger(__name__)


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Natural language user question")


class QueryResponse(BaseModel):
    answer: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    dataframe = load_tickets()
    app.state.assistant = build_assistant(dataframe)
    app.state.row_count = len(dataframe)
    yield


app = FastAPI(title="Support Ticket Assistant", version="1.0.0", lifespan=lifespan)


@app.get("/")
def health() -> dict[str, Any]:
    return {"status": "ok", "rows_loaded": getattr(app.state, "row_count", 0)}


@app.post("/query", response_model=QueryResponse)
def query(payload: QueryRequest) -> QueryResponse:
    assistant = getattr(app.state, "assistant", None)
    if assistant is None:
        raise HTTPException(status_code=503, detail="Assistant is not ready.")

    try:
        answer = assistant.answer(payload.question)
        return QueryResponse(answer=answer)
    except LLMError as exc:
        LOGGER.exception("LLM error")
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Query processing error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

