"""
LangGraph Hierarchical Workflow — The Core Multi-Agent Orchestration Graph.

Implements the full pipeline with:
- Conditional routing (Supervisor → SQL | Doc | Hybrid)
- Self-reflection loop (Relevance Grader → Query Rewriter)
- Hallucination guard before final answer emission
- Telemetry tracking across all hops
"""

import os
import sys
from typing import Literal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.agents.state import AgentState
from src.agents.nodes import (
    supervisor_node,
    document_rag_node,
    relevance_grader_node,
    query_rewriter_node,
    sql_analyst_node,
    hallucination_grader_node,
    synthesis_node,
)
from src.telemetry.metrics import TelemetryTracker

try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False


MAX_REFLECTION_ITERATIONS = 2  # Max self-correction loops before fallback


# ── Conditional Edge Functions ────────────────────────────────────────────────

def route_after_supervisor(state: AgentState) -> Literal["doc_rag", "sql_analyst", "doc_and_sql"]:
    route = state.get("route", "doc")
    if route == "sql":
        return "sql_analyst"
    elif route == "hybrid":
        return "doc_and_sql"
    return "doc_rag"


def route_after_grader(state: AgentState) -> Literal["query_rewriter", "hallucination_grader"]:
    grade = state.get("relevance_grade", "relevant")
    iterations = state.get("iteration", 0)
    if grade == "irrelevant" and iterations < MAX_REFLECTION_ITERATIONS:
        return "query_rewriter"
    return "hallucination_grader"


def route_after_hallucination(state: AgentState) -> Literal["synthesis", "query_rewriter"]:
    grade = state.get("hallucination_grade", "grounded")
    iterations = state.get("iteration", 0)
    if grade == "hallucinated" and iterations < MAX_REFLECTION_ITERATIONS:
        return "query_rewriter"
    return "synthesis"


# ── Build LangGraph Workflow ───────────────────────────────────────────────────

def build_graph():
    """Construct and compile the full LangGraph StateGraph."""
    if not LANGGRAPH_AVAILABLE:
        return None

    workflow = StateGraph(AgentState)

    # Add all nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("doc_rag", document_rag_node)
    workflow.add_node("sql_analyst", sql_analyst_node)
    workflow.add_node("relevance_grader", relevance_grader_node)
    workflow.add_node("query_rewriter", query_rewriter_node)
    workflow.add_node("hallucination_grader", hallucination_grader_node)
    workflow.add_node("synthesis", synthesis_node)

    # Set entry point
    workflow.set_entry_point("supervisor")

    # Conditional routing after Supervisor
    workflow.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "doc_rag": "doc_rag",
            "sql_analyst": "sql_analyst",
            "doc_and_sql": "doc_rag",   # Hybrid: start with doc, then sql in synthesis
        }
    )

    # After document retrieval → relevance grading
    workflow.add_edge("doc_rag", "relevance_grader")

    # Conditional routing after grader (self-reflection loop)
    workflow.add_conditional_edges(
        "relevance_grader",
        route_after_grader,
        {
            "query_rewriter": "query_rewriter",
            "hallucination_grader": "hallucination_grader",
        }
    )

    # Query rewriter loops back to doc retrieval
    workflow.add_edge("query_rewriter", "doc_rag")

    # SQL path goes directly to hallucination check then synthesis
    workflow.add_edge("sql_analyst", "hallucination_grader")

    # Hallucination guard
    workflow.add_conditional_edges(
        "hallucination_grader",
        route_after_hallucination,
        {
            "query_rewriter": "query_rewriter",
            "synthesis": "synthesis",
        }
    )

    # Terminal: synthesis → END
    workflow.add_edge("synthesis", END)

    return workflow.compile()


# ── Fallback: Pure Python execution (no LangGraph dependency) ─────────────────

def run_pipeline_fallback(query: str) -> dict:
    """
    Runs the full multi-agent pipeline without LangGraph.
    Uses direct function calls to simulate the graph traversal.
    Useful for development without langgraph installed.
    """
    tracker = TelemetryTracker(trace_id=f"trace_{hash(query) % 100000}")

    state: AgentState = {
        "query": query,
        "rewritten_query": "",
        "route": "",
        "iteration": 0,
        "retrieved_docs": [],
        "sql_results": {},
        "generated_sql": "",
        "relevance_grade": "",
        "hallucination_grade": "",
        "final_answer": "",
        "citations": [],
        "telemetry": {},
        "error": None,
        "_tracker": tracker,  # Injected tracker
    }

    # Step 1: Supervisor routing
    state = supervisor_node(state)
    route = state["route"]

    # Step 2: Delegate to specialist agents
    if route == "sql":
        state = sql_analyst_node(state)
    else:
        # Doc RAG with self-reflection loop
        for attempt in range(MAX_REFLECTION_ITERATIONS + 1):
            state = document_rag_node(state)
            state = relevance_grader_node(state)
            if state["relevance_grade"] == "relevant" or attempt >= MAX_REFLECTION_ITERATIONS:
                break
            state = query_rewriter_node(state)

        if route == "hybrid":
            state = sql_analyst_node(state)

    # Step 3: Hallucination guard
    state = hallucination_grader_node(state)

    # Step 4: Synthesis
    state = synthesis_node(state, tracker=tracker)

    return state


# ── Primary Entry Point ────────────────────────────────────────────────────────

def run_query(query: str) -> dict:
    """
    Main entry point. Runs the full multi-agent pipeline with accurate telemetry.
    Uses run_pipeline_fallback which correctly threads the TelemetryTracker
    through all agent nodes via the shared state dict.
    """
    return run_pipeline_fallback(query)
