"""
All LangGraph agent node functions.
Implements the full Hierarchical Multi-Agent RAG pipeline:
  - Supervisor (Router)
  - Document RAG Agent
  - SQL Analyst Agent
  - Relevance Grader (Self-Reflection)
  - Query Rewriter (Self-Correction loop)
  - Hallucination Grader
  - Synthesis Agent
"""

import os
import sys
import json
from typing import Any, Dict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.agents.state import AgentState
from src.agents.llm_client import get_llm
from src.storage.vector_store import VectorStore
from src.storage.sql_engine import SQLEngine
from src.telemetry.metrics import TelemetryTracker

# ── Shared resources (lazy-loaded singletons) ──────────────────────────────
_llm = None
_vector_store = None
_sql_engine = None

def _get_llm():
    global _llm
    if _llm is None:
        _llm = get_llm()
    return _llm

def _get_vector_store():
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
        _vector_store.ingest_documents()
    return _vector_store

def _get_sql_engine():
    global _sql_engine
    if _sql_engine is None:
        _sql_engine = SQLEngine()
    return _sql_engine


# ─────────────────────────────────────────────────────────────────────────────
# NODE 1: SUPERVISOR — routes query to the right specialist agent
# ─────────────────────────────────────────────────────────────────────────────
def supervisor_node(state: AgentState) -> AgentState:
    """
    👔 Supervisor Agent: Analyses the user query and decides routing:
    - 'doc'    → Document RAG agent (unstructured knowledge base)
    - 'sql'    → SQL Analyst agent (structured database)
    - 'hybrid' → Both agents in sequence
    """
    tracker: TelemetryTracker = state.get("_tracker")
    span = tracker.start_span("Supervisor", "route_query") if tracker else None

    llm = _get_llm()
    prompt = f"""You are an enterprise AI routing agent. 
Analyse the following query and decide which data source to use.

Query: "{state['query']}"

Available routes:
- "doc"    → For policy, technical specs, runbooks, security guidelines (unstructured text)
- "sql"    → For employee data, sales numbers, financial metrics, project info (structured DB)
- "hybrid" → When both document context and structured data are needed

Respond ONLY with valid JSON: {{"route": "<doc|sql|hybrid>"}}"""

    response = llm.invoke(prompt)
    input_tokens = getattr(getattr(response, "usage_metadata", None), "input_tokens", len(prompt.split()) * 2)
    output_tokens = getattr(getattr(response, "usage_metadata", None), "output_tokens", 10)

    if span:
        span.finish(input_tokens=input_tokens, output_tokens=output_tokens, details={"prompt_len": len(prompt)})
        tracker.record_usage(input_tokens, output_tokens)

    try:
        result = json.loads(response.content)
        route = result.get("route", "doc")
    except (json.JSONDecodeError, AttributeError):
        route = "doc"

    return {**state, "route": route, "iteration": 0}


# ─────────────────────────────────────────────────────────────────────────────
# NODE 2: DOCUMENT RAG AGENT — retrieves and returns relevant doc chunks
# ─────────────────────────────────────────────────────────────────────────────
def document_rag_node(state: AgentState) -> AgentState:
    """
    📚 Document RAG Agent: Embeds the query and retrieves top-k document chunks.
    Uses the rewritten query if available (self-correction loop).
    """
    tracker: TelemetryTracker = state.get("_tracker")
    span = tracker.start_span("DocumentRAGAgent", "retrieve_documents") if tracker else None

    vs = _get_vector_store()
    effective_query = state.get("rewritten_query") or state["query"]
    retrieved = vs.similarity_search(effective_query, top_k=3)

    if span:
        span.finish(
            input_tokens=len(effective_query.split()),
            output_tokens=sum(len(d["content"].split()) for d in retrieved),
            details={"num_docs": len(retrieved), "query": effective_query}
        )

    return {**state, "retrieved_docs": retrieved}


# ─────────────────────────────────────────────────────────────────────────────
# NODE 3: RELEVANCE GRADER — Self-Reflection: are retrieved docs relevant?
# ─────────────────────────────────────────────────────────────────────────────
def relevance_grader_node(state: AgentState) -> AgentState:
    """
    🔍 Relevance Grader: Applies self-reflection to judge whether the retrieved
    documents actually answer the user query. If not, triggers query rewriting.
    """
    tracker: TelemetryTracker = state.get("_tracker")
    span = tracker.start_span("RelevanceGrader", "grade_retrieved_docs") if tracker else None

    llm = _get_llm()
    docs_summary = "\n---\n".join(d["content"][:300] for d in state.get("retrieved_docs", []))

    prompt = f"""You are a strict relevance evaluator.

User Query: "{state['query']}"

Retrieved document excerpts:
{docs_summary}

Task: Determine if the documents contain information that meaningfully answers the query.
Respond ONLY with valid JSON: {{"grade": "relevant"}} or {{"grade": "irrelevant"}}"""

    response = llm.invoke(prompt)
    input_tokens = getattr(getattr(response, "usage_metadata", None), "input_tokens", len(prompt.split()) * 2)
    output_tokens = getattr(getattr(response, "usage_metadata", None), "output_tokens", 5)

    if span:
        span.finish(input_tokens=input_tokens, output_tokens=output_tokens)
        tracker.record_usage(input_tokens, output_tokens)

    try:
        grade = json.loads(response.content).get("grade", "relevant")
    except (json.JSONDecodeError, AttributeError):
        grade = "relevant"

    return {**state, "relevance_grade": grade}


# ─────────────────────────────────────────────────────────────────────────────
# NODE 4: QUERY REWRITER — Self-Correction loop
# ─────────────────────────────────────────────────────────────────────────────
def query_rewriter_node(state: AgentState) -> AgentState:
    """
    🔄 Query Rewriter: When retrieved documents are graded as irrelevant,
    this agent reformulates the query to improve retrieval on the next attempt.
    """
    tracker: TelemetryTracker = state.get("_tracker")
    span = tracker.start_span("QueryRewriter", "rewrite_query") if tracker else None

    llm = _get_llm()
    prompt = f"""You are a query optimisation expert.

The following query failed to retrieve relevant documents:
Original Query: "{state['query']}"

Reformulate this query to be more specific and likely to match enterprise documents.
Focus on: expanding acronyms, adding enterprise context, and specifying the domain.
Respond ONLY with the improved query text (no JSON, no explanation)."""

    response = llm.invoke(prompt)
    input_tokens = getattr(getattr(response, "usage_metadata", None), "input_tokens", len(prompt.split()) * 2)
    output_tokens = getattr(getattr(response, "usage_metadata", None), "output_tokens", len(response.content.split()))

    if span:
        span.finish(input_tokens=input_tokens, output_tokens=output_tokens,
                    details={"new_query": response.content[:100]})
        tracker.record_usage(input_tokens, output_tokens)

    return {
        **state,
        "rewritten_query": response.content.strip(),
        "iteration": state.get("iteration", 0) + 1,
    }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 5: SQL ANALYST AGENT — text-to-SQL over structured database
# ─────────────────────────────────────────────────────────────────────────────
def sql_analyst_node(state: AgentState) -> AgentState:
    """
    📊 SQL Analyst Agent: Generates a SQL query from the user's natural-language
    request and executes it against the enterprise SQLite database.
    """
    tracker: TelemetryTracker = state.get("_tracker")
    span = tracker.start_span("SQLAnalystAgent", "generate_and_execute_sql") if tracker else None

    llm = _get_llm()
    sql_eng = _get_sql_engine()
    schema = sql_eng.get_schema()

    prompt = f"""You are an expert SQL analyst with access to an enterprise database.

Database Schema:
{schema}

User Question: "{state['query']}"

Write a single correct SQL query to answer this question. 
Return ONLY the SQL query inside a ```sql ... ``` code block. 
Use only SELECT statements. Do not use DROP, INSERT, UPDATE, DELETE."""

    response = llm.invoke(prompt)
    input_tokens = getattr(getattr(response, "usage_metadata", None), "input_tokens", len(prompt.split()) * 2)
    output_tokens = getattr(getattr(response, "usage_metadata", None), "output_tokens", 30)

    # Extract SQL from response
    sql_query = sql_eng.extract_sql_from_response(response.content)
    sql_results = {}
    if sql_query:
        sql_results = sql_eng.execute_query(sql_query)
    else:
        sql_results = {"success": False, "error": "Could not extract valid SQL from LLM response.", "rows": []}

    if span:
        span.finish(input_tokens=input_tokens, output_tokens=output_tokens,
                    details={"sql": sql_query, "row_count": sql_results.get("row_count", 0)})
        tracker.record_usage(input_tokens, output_tokens)

    return {**state, "generated_sql": sql_query, "sql_results": sql_results}


# ─────────────────────────────────────────────────────────────────────────────
# NODE 6: HALLUCINATION GRADER — verifies answer is grounded in context
# ─────────────────────────────────────────────────────────────────────────────
def hallucination_grader_node(state: AgentState) -> AgentState:
    """
    🛡️ Hallucination Grader: Checks whether a preliminary answer is grounded
    in the retrieved documents and SQL results (not hallucinated).
    """
    tracker: TelemetryTracker = state.get("_tracker")
    span = tracker.start_span("HallucinationGrader", "verify_groundedness") if tracker else None

    llm = _get_llm()
    context_parts = []
    for d in state.get("retrieved_docs", []):
        context_parts.append(d["content"][:200])
    if state.get("sql_results", {}).get("rows"):
        context_parts.append(str(state["sql_results"]["rows"][:5]))

    context = "\n".join(context_parts) or "No context retrieved."
    answer_preview = state.get("final_answer", "")[:500]

    prompt = f"""You are a hallucination detection system.

Retrieved Context:
{context}

Preliminary Answer:
{answer_preview}

Does the answer make claims that are NOT supported by the retrieved context?
Respond ONLY with valid JSON: {{"grade": "grounded"}} or {{"grade": "hallucinated"}}"""

    response = llm.invoke(prompt)
    input_tokens = getattr(getattr(response, "usage_metadata", None), "input_tokens", len(prompt.split()) * 2)
    output_tokens = getattr(getattr(response, "usage_metadata", None), "output_tokens", 5)

    if span:
        span.finish(input_tokens=input_tokens, output_tokens=output_tokens)
        tracker.record_usage(input_tokens, output_tokens)

    try:
        grade = json.loads(response.content).get("grade", "grounded")
    except (json.JSONDecodeError, AttributeError):
        grade = "grounded"

    return {**state, "hallucination_grade": grade}


# ─────────────────────────────────────────────────────────────────────────────
# NODE 7: SYNTHESIS AGENT — composes the final grounded answer with citations
# ─────────────────────────────────────────────────────────────────────────────
def synthesis_node(state: AgentState, tracker: TelemetryTracker = None) -> AgentState:
    """
    📝 Synthesis Agent: Combines retrieved document context + SQL results
    to compose a coherent, cited, grounded final answer.
    """
    _tracker: TelemetryTracker = state.get("_tracker") or tracker
    span = _tracker.start_span("SynthesisAgent", "compose_final_answer") if _tracker else None

    llm = _get_llm()

    # Build context block
    doc_context = ""
    citations = []
    for i, doc in enumerate(state.get("retrieved_docs", []), 1):
        doc_context += f"\n[{i}] Source: {doc['source']} (score: {doc['similarity_score']})\n{doc['content'][:400]}\n"
        citations.append(f"[{i}] {doc['source']}")

    sql_context = ""
    if state.get("sql_results", {}).get("success") and state["sql_results"].get("rows"):
        rows = state["sql_results"]["rows"][:10]
        cols = state["sql_results"].get("columns", [])
        sql_context = f"\nDatabase Results ({state.get('generated_sql', 'SQL query')}):\n"
        sql_context += " | ".join(cols) + "\n"
        for row in rows:
            sql_context += " | ".join(str(row.get(c, "")) for c in cols) + "\n"
        citations.append("[DB] Enterprise SQLite Database")

    prompt = f"""You are a helpful enterprise AI assistant. 
Answer the user's question using ONLY the provided context.
Be concise, structured, and cite your sources using [n] notation.

User Query: "{state['query']}"

Document Context:
{doc_context or "No documents retrieved."}

{sql_context}

Provide a clear, professional answer with citations. 
If information is unavailable, say so explicitly rather than guessing."""

    response = llm.invoke(prompt)
    input_tokens = getattr(getattr(response, "usage_metadata", None), "input_tokens", len(prompt.split()) * 2)
    output_tokens = getattr(getattr(response, "usage_metadata", None), "output_tokens", len(response.content.split()))

    if span:
        span.finish(input_tokens=input_tokens, output_tokens=output_tokens,
                    details={"answer_len": len(response.content)})
        if _tracker:
            _tracker.record_usage(input_tokens, output_tokens)

    # Attach telemetry summary to state
    telemetry_summary = _tracker.get_summary() if _tracker else {}

    return {
        **state,
        "final_answer": response.content.strip(),
        "citations": citations,
        "telemetry": telemetry_summary,
    }
