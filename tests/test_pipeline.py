"""
Tests for the Enterprise RAG Multi-Agent System.
Tests the telemetry tracker, SQL engine, vector store, and pipeline integration.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.telemetry.metrics import TelemetryTracker, AgentSpan
from src.storage.sql_engine import SQLEngine
from src.agents.workflow import run_pipeline_fallback


# ── Telemetry Tests ───────────────────────────────────────────────────────────

def test_tracker_span_lifecycle():
    tracker = TelemetryTracker(trace_id="test-001")
    span = tracker.start_span("TestAgent", "test_action")
    span.finish(input_tokens=100, output_tokens=50)

    assert span.status == "completed"
    assert span.latency_ms >= 0
    assert span.input_tokens == 100
    assert span.output_tokens == 50
    assert span.estimated_cost_usd >= 0


def test_tracker_summary_fields():
    tracker = TelemetryTracker(trace_id="test-002")
    span = tracker.start_span("Agent1", "action1")
    span.finish(input_tokens=200, output_tokens=80)
    tracker.record_usage(200, 80)

    summary = tracker.get_summary()
    assert summary["trace_id"] == "test-002"
    assert summary["total_input_tokens"] == 200
    assert summary["total_output_tokens"] == 80
    assert summary["span_count"] == 1
    assert len(summary["spans"]) == 1
    assert summary["tokens_per_sec"] >= 0


def test_cost_estimation():
    tracker = TelemetryTracker(trace_id="test-003")
    span = tracker.start_span("LLMAgent", "generate")
    span.finish(input_tokens=1_000_000, output_tokens=1_000_000)
    # At Gemini pricing: $0.075 input + $0.30 output = $0.375
    assert abs(span.estimated_cost_usd - 0.375) < 0.001


# ── SQL Engine Tests ───────────────────────────────────────────────────────────

def test_sql_engine_seeding(tmp_path):
    db_path = str(tmp_path / "test.db")
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from data.sql.seed_db import seed_database
    seed_database(db_path)

    engine = SQLEngine(db_path=db_path)
    result = engine.execute_query("SELECT COUNT(*) as cnt FROM employees;")
    assert result["success"] is True
    assert result["rows"][0]["cnt"] == 10


def test_sql_engine_rejects_mutations(tmp_path):
    db_path = str(tmp_path / "test2.db")
    from data.sql.seed_db import seed_database
    seed_database(db_path)

    engine = SQLEngine(db_path=db_path)
    result = engine.execute_query("DROP TABLE employees;")
    assert result["success"] is False
    assert "SELECT" in result["error"]


def test_sql_extraction():
    engine = SQLEngine.__new__(SQLEngine)  # Bypass __init__
    engine.db_path = ""

    text = "Sure! Here is the query:\n```sql\nSELECT name FROM employees;\n```"
    sql = engine.extract_sql_from_response(text)
    assert "SELECT" in sql.upper()


# ── Integration Pipeline Test ─────────────────────────────────────────────────

def test_pipeline_doc_query():
    result = run_pipeline_fallback("What is the remote work policy?")
    assert result.get("final_answer"), "Should produce a final answer"
    assert result.get("route") in ("doc", "sql", "hybrid"), "Should have a route"
    assert isinstance(result.get("telemetry"), dict), "Should have telemetry"


def test_pipeline_sql_query():
    result = run_pipeline_fallback("How many employees are there?")
    assert result.get("final_answer"), "Should produce a final answer"
    assert isinstance(result.get("telemetry"), dict)


def test_pipeline_telemetry_has_spans():
    result = run_pipeline_fallback("What is the security policy?")
    tel = result.get("telemetry", {})
    assert tel.get("span_count", 0) > 0, "Should have recorded at least one agent span"
    assert "spans" in tel
    agents = [s["agent"] for s in tel["spans"]]
    assert "Supervisor" in agents


def test_pipeline_has_citations():
    result = run_pipeline_fallback("What are the onboarding steps?")
    # Doc queries should have citations
    assert isinstance(result.get("citations"), list)
