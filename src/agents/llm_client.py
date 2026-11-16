"""
LLM Client — wraps Google Gemini (via langchain-google-genai).
Falls back to a mock LLM for local development without API keys.
"""

import os
import json
import time
import random
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class MockLLM:
    """
    Zero-dependency mock LLM for running the full agent graph
    without any API keys. Returns deterministic, realistic responses
    for routing, SQL generation, grading, and synthesis tasks.
    """

    def _route(self, query: str) -> str:
        q = query.lower()
        if any(k in q for k in ["how many", "total", "salary", "employee", "sales", "revenue", "count", "list all", "which department"]):
            return '{"route": "sql"}'
        if any(k in q for k in ["policy", "runbook", "security", "onboarding", "incident", "deployment", "spec"]):
            return '{"route": "doc"}'
        return '{"route": "hybrid"}'

    def _sql(self, query: str) -> str:
        q = query.lower()
        if "highest salary" in q or "top salary" in q or "max salary" in q:
            return "```sql\nSELECT name, department, salary_usd FROM employees ORDER BY salary_usd DESC LIMIT 3;\n```"
        if "engineering" in q:
            return "```sql\nSELECT name, role, salary_usd FROM employees WHERE department='Engineering' AND is_active=1;\n```"
        if "sales" in q and "q3" in q:
            return "```sql\nSELECT e.name, s.customer, s.deal_value_usd, s.status FROM sales s JOIN employees e ON s.employee_id=e.id WHERE s.quarter='Q3-2024';\n```"
        if "project" in q:
            return "```sql\nSELECT p.name, p.status, p.budget_usd, e.name as lead FROM projects p LEFT JOIN employees e ON p.lead_employee_id=e.id;\n```"
        return "```sql\nSELECT name, department, role FROM employees WHERE is_active=1 LIMIT 10;\n```"

    def _grade_relevance(self) -> str:
        return '{"grade": "relevant"}'

    def _grade_hallucination(self) -> str:
        return '{"grade": "grounded"}'

    def _rewrite(self, query: str) -> str:
        return f"Provide detailed information about: {query}"

    def _synthesize(self, prompt: str) -> str:
        # Extract just the User Query line from the prompt
        import re
        match = re.search(r'User Query: "(.+?)"', prompt)
        query = match.group(1) if match else "your query"

        # Extract SQL results if present
        sql_match = re.search(r"Database Results.*?:\n(.*?)(?:\n\nProvide|$)", prompt, re.DOTALL)
        db_context = sql_match.group(1).strip()[:500] if sql_match else ""

        # Extract document context if present
        doc_match = re.search(r"\[1\] Source:.*?(?=\[2\]|\nDatabase|\nProvide|$)", prompt, re.DOTALL)
        doc_context = doc_match.group(0).strip()[:300] if doc_match else ""

        answer_parts = [f"Based on the enterprise knowledge base, here is what I found for: **{query}**\n"]
        if doc_context:
            answer_parts.append(f"From internal documents:\n{doc_context[:200]}...")
        if db_context:
            answer_parts.append(f"\nFrom structured database:\n{db_context}")
        if not doc_context and not db_context:
            answer_parts.append("The requested information was not found in the available enterprise data sources.")

        answer_parts.append("\n*This answer was synthesized from internal enterprise documents and structured data.*")
        return "\n".join(answer_parts)

    def invoke(self, prompt: str) -> "MockLLMResponse":
        time.sleep(0.05)  # Simulate small network delay
        p = prompt.lower()
        if "route" in p and "json" in p:
            content = self._route(prompt)
        elif "sql query" in p or "write a sql" in p or "generate sql" in p:
            content = self._sql(prompt)
        elif "hallucination" in p:
            content = self._grade_hallucination()
        elif "relevant" in p and "grade" in p:
            content = self._grade_relevance()
        elif "rewrite" in p or "reformulate" in p:
            content = self._rewrite(prompt)
        else:
            content = self._synthesize(prompt)

        return MockLLMResponse(content=content)


class MockLLMResponse:
    def __init__(self, content: str):
        self.content = content
        # Simulate token counts
        self.usage_metadata = type("usage", (), {
            "input_tokens": len(content.split()) * 2,
            "output_tokens": len(content.split()),
        })()


class ResilientLLM:
    """
    Wraps ChatGoogleGenerativeAI with automatic fallback to MockLLM
    if the API key has expired, exhausted billing/credits, or lacks internet.
    """
    def __init__(self, primary_llm, fallback_llm: MockLLM):
        self.primary = primary_llm
        self.fallback = fallback_llm
        self.using_fallback = False

    def invoke(self, prompt: str):
        if not self.using_fallback:
            try:
                return self.primary.invoke(prompt)
            except Exception as e:
                print(f"\n[!] Gemini API notice: {type(e).__name__} ({str(e)[:120]}...). Falling back to local MockLLM.\n")
                self.using_fallback = True
        return self.fallback.invoke(prompt)


def get_llm(model: str = "gemini-1.5-flash"):
    """
    Returns a real Gemini LLM if GOOGLE_API_KEY is set, wrapped with
    automatic fallback to MockLLM on quota/billing issues.
    """
    api_key = os.getenv("GOOGLE_API_KEY", "")
    mock = MockLLM()
    if api_key and api_key != "your_google_api_key_here":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            real_llm = ChatGoogleGenerativeAI(
                model=model,
                google_api_key=api_key,
                temperature=0.0,
                convert_system_message_to_human=True
            )
            return ResilientLLM(primary_llm=real_llm, fallback_llm=mock)
        except ImportError:
            pass
    return mock
