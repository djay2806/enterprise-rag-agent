"""
FastAPI backend — exposes the multi-agent RAG system as a REST API.
Routes:
  POST /query       — Run a query through the full multi-agent pipeline
  GET  /health      — Health check
  GET  /metrics     — Get latest telemetry summary
  GET  /schema      — Get database schema
  GET  /docs-count  — Get number of indexed documents
"""

import os
import sys
from typing import Optional
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.agents.workflow import run_query, LANGGRAPH_AVAILABLE
from src.storage.vector_store import VectorStore
from src.storage.sql_engine import SQLEngine


# ── App Setup ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="🏢 Enterprise RAG Multi-Agent API",
    description=(
        "Hierarchical Multi-Agent RAG System with LangGraph orchestration. "
        "Features: Supervisor routing, Document RAG, SQL analytics, "
        "self-reflection loops, hallucination detection, and LLM metrics tracing."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Keep last N telemetry results in memory for the /metrics endpoint
_metrics_history = []


# ── Request / Response Models ──────────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000, example="What is the remote work policy?")


class QueryResponse(BaseModel):
    query: str
    answer: str
    citations: list[str]
    route_used: str
    reflection_iterations: int
    relevance_grade: str
    hallucination_grade: str
    telemetry: dict
    timestamp: str


class HealthResponse(BaseModel):
    status: str
    langgraph_available: bool
    llm_mode: str
    indexed_documents: int
    timestamp: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Check system health, LangGraph availability, and document index status."""
    vs = VectorStore()
    api_key = os.getenv("GOOGLE_API_KEY", "")
    llm_mode = "gemini-api" if (api_key and api_key != "your_google_api_key_here") else "mock-llm"
    return HealthResponse(
        status="healthy",
        langgraph_available=LANGGRAPH_AVAILABLE,
        llm_mode=llm_mode,
        indexed_documents=vs.count(),
        timestamp=datetime.utcnow().isoformat() + "Z"
    )


@app.post("/query", response_model=QueryResponse, tags=["Agent"])
async def run_agent_query(request: QueryRequest):
    """
    Run the full hierarchical multi-agent RAG pipeline on a query.
    Returns the grounded answer, citations, routing decisions, and LLM telemetry.
    """
    try:
        result = run_query(request.query)

        response = QueryResponse(
            query=request.query,
            answer=result.get("final_answer", "No answer generated."),
            citations=result.get("citations", []),
            route_used=result.get("route", "unknown"),
            reflection_iterations=result.get("iteration", 0),
            relevance_grade=result.get("relevance_grade", "N/A"),
            hallucination_grade=result.get("hallucination_grade", "N/A"),
            telemetry=result.get("telemetry", {}),
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

        # Store metrics history
        _metrics_history.append(result.get("telemetry", {}))
        if len(_metrics_history) > 50:
            _metrics_history.pop(0)

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent pipeline error: {str(e)}")


@app.get("/metrics", tags=["Observability"])
async def get_metrics():
    """Return the latest LLM telemetry summary (tokens/sec, cost, latency spans)."""
    if not _metrics_history:
        return {"message": "No queries run yet. POST to /query first."}
    return {
        "latest": _metrics_history[-1],
        "total_queries_tracked": len(_metrics_history),
        "cumulative_cost_usd": round(
            sum(m.get("total_cost_usd", 0) for m in _metrics_history), 6
        ),
        "avg_latency_ms": round(
            sum(m.get("total_latency_ms", 0) for m in _metrics_history) / len(_metrics_history), 2
        ),
    }


@app.get("/schema", tags=["Data"])
async def get_db_schema():
    """Return the enterprise SQL database schema."""
    engine = SQLEngine()
    return {"schema": engine.get_schema()}


@app.get("/docs-count", tags=["Data"])
async def get_docs_count():
    """Return the number of documents currently indexed in the vector store."""
    vs = VectorStore()
    return {"indexed_documents": vs.count()}


@app.get("/", tags=["System"])
async def root():
    return {
        "name": "Enterprise Hierarchical Multi-Agent RAG System",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "query_endpoint": "POST /query",
    }
