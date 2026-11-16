# 🏢 Enterprise Hierarchical Multi-Agent RAG System

A **production-grade, interview-ready AI system** built with LangGraph, ChromaDB, and FastAPI.  
Demonstrates every key skill from Google's AI Internship JD: multi-agent orchestration, RAG pipelines, self-reflection, hybrid data retrieval, and LLM-native metrics.

---

## 🏗️ Architecture

```
User Query
    │
    ▼
👔 Supervisor Agent (LangGraph Router)
    │
    ├──► 📚 Document RAG Agent (ChromaDB + sentence-transformers)
    │         │
    │         ▼
    │    🔍 Relevance Grader (Self-Reflection)
    │         │
    │    ┌────┴────┐
    │    ▼         ▼
    │  Relevant   Irrelevant → 🔄 Query Rewriter (loops back)
    │    │
    │    ▼
    ├──► 📊 SQL Analyst Agent (Text-to-SQL → SQLite)
    │
    ▼
🛡️ Hallucination Grader
    │
    ▼
📝 Synthesis Agent (Final grounded answer + citations)
    │
    ▼
⏱️ Telemetry: tokens/sec · cost/request · per-agent latency spans
```

---

## ✅ JD Requirements Covered

| Google JD Requirement | Implementation |
|---|---|
| Python + DSA | Typed dataclasses, state machines, Python 3.13 |
| Multi-agent (LangGraph, CrewAI, ADK) | **LangGraph** StateGraph with conditional edges |
| RAG + Vector Databases | **ChromaDB** + SentenceTransformers embeddings |
| Structured + Unstructured pipelines | SQLite (structured) + ChromaDB (unstructured) |
| GCP Cloud Platform | FastAPI service containerizable for Cloud Run |
| ReAct / Self-Reflection patterns | Relevance Grader + Query Rewriter loop |
| Hierarchical Delegation | Supervisor → Specialist Agents (LangGraph) |
| LLM tokens/sec, cost-per-request | Built-in `TelemetryTracker` per agent span |
| Granular tracing & state management | Full span trace across all 7 agent hops |

---

## 🚀 Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the CLI (no API key needed — works with mock LLM)
```bash
# Interactive mode
python cli.py

# Demo mode (runs all 7 sample queries)
python cli.py --demo

# Single query
python cli.py --query "What is the remote work policy?"
```

### 3. Run the FastAPI server
```bash
uvicorn src.api.server:app --reload --port 8000
```
Then open: http://localhost:8000/docs

### 4. Use a real Gemini API key (optional)
```bash
# Copy and edit the env file
copy .env.example .env
# Set GOOGLE_API_KEY=your_key_here
```

### 5. Run tests
```bash
pytest tests/ -v
```

---

## 📂 Project Structure

```
enterprise-rag-agent/
├── cli.py                        # Interactive CLI playground
├── requirements.txt
├── .env.example
├── ARCHITECTURE.md               # Full architecture diagram
│
├── src/
│   ├── agents/
│   │   ├── state.py              # LangGraph shared TypedDict state
│   │   ├── llm_client.py         # Gemini or MockLLM (zero-key fallback)
│   │   ├── nodes.py              # All 7 agent node functions
│   │   └── workflow.py           # LangGraph StateGraph + fallback runner
│   ├── storage/
│   │   ├── vector_store.py       # ChromaDB + sentence-transformers
│   │   └── sql_engine.py         # SQLite text-to-SQL engine
│   ├── telemetry/
│   │   └── metrics.py            # TelemetryTracker: spans, tokens/sec, cost
│   └── api/
│       └── server.py             # FastAPI REST API
│
├── data/
│   ├── docs/sample_docs.py       # 5 enterprise document corpus
│   └── sql/seed_db.py            # SQLite seeder (employees, sales, projects)
│
└── tests/
    └── test_pipeline.py          # Pytest suite: telemetry, SQL, integration
```

---

## 📊 Sample Queries

| Type | Example Query |
|---|---|
| Document RAG | *"What is the remote work policy?"* |
| SQL Analytics | *"Who are the top 3 highest-paid employees?"* |
| SQL Analytics | *"Show me all Q3-2024 sales deals and their values."* |
| Document RAG | *"What are the security data classification levels?"* |
| Hybrid | *"What was TechCorp's Q3 revenue and which projects are active?"* |
| SRE Runbook | *"What should I do when LangGraph agents get stuck in an infinite loop?"* |

---

## 🔑 API Keys

| Key | Required? | Where to Get |
|---|---|---|
| `GOOGLE_API_KEY` | Optional | [Google AI Studio](https://aistudio.google.com) — free tier |
| `PINECONE_API_KEY` | Optional | [Pinecone Console](https://app.pinecone.io) — free starter |
| `LANGCHAIN_API_KEY` | Optional | [LangSmith](https://smith.langchain.com) — free dev tier |

> **Without any keys**, the system runs using a built-in `MockLLM` that returns realistic responses — perfect for development and demos.

---

## 🎓 Interview Talking Points

1. **Why LangGraph over CrewAI?** — LangGraph gives explicit control over state machines and conditional edges, which is essential for production debugging and observability.
2. **How do you prevent infinite self-reflection loops?** — `MAX_REFLECTION_ITERATIONS = 2` hard cap with fallback to best-effort answer.
3. **How do you handle hallucinations?** — Hallucination Grader node cross-checks the generated answer against retrieved context before emitting it.
4. **How is cost tracked?** — Each agent span records `input_tokens` and `output_tokens`, which are priced at Gemini Flash rates and accumulated into `total_cost_usd`.
5. **How would you scale this to GCP?** — Containerize with Docker, deploy to Cloud Run (auto-scaling), swap ChromaDB for Vertex Vector Search, and use Vertex AI for Gemini.
