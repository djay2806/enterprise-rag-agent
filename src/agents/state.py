"""
Shared LangGraph State schema used across all agents in the hierarchy.
All agents read from and write to this TypedDict state.
"""

from typing import List, Optional, Any, Dict
from typing_extensions import TypedDict


class AgentState(TypedDict):
    # Core conversation
    query: str                              # Original user query
    rewritten_query: str                    # Reformulated query (by query rewriter)
    route: str                              # Routing decision: "doc", "sql", "hybrid"
    iteration: int                          # Self-reflection loop counter

    # Retrieved context
    retrieved_docs: List[Dict[str, Any]]    # From vector store
    sql_results: Dict[str, Any]             # From SQL engine
    generated_sql: str                      # SQL produced by LLM

    # Grading
    relevance_grade: str                    # "relevant" | "irrelevant"
    hallucination_grade: str                # "grounded" | "hallucinated"

    # Final answer
    final_answer: str                       # Synthesized output
    citations: List[str]                    # Source references
    
    # Telemetry
    telemetry: Dict[str, Any]              # Metrics summary from TelemetryTracker
    error: Optional[str]                    # Error message if something fails
