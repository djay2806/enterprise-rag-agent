"""
Sample enterprise documents for the RAG system.
These simulate a corporate knowledge base with mixed unstructured content.
"""

SAMPLE_DOCS = [
    {
        "id": "doc_001",
        "source": "employee_handbook.txt",
        "content": """
        Employee Onboarding Policy - TechCorp Inc.
        
        Welcome to TechCorp! All new employees must complete the following within their first 30 days:
        1. Complete security training via the internal LMS portal.
        2. Set up two-factor authentication (2FA) on all company accounts.
        3. Submit signed NDA and IP agreements to HR@techcorp.com.
        4. Book a 1:1 with your team lead within the first week.
        5. Complete mandatory diversity & inclusion training (D&I).
        
        Remote Work Policy:
        Employees may work remotely up to 3 days per week. Core collaboration hours are 10AM - 3PM IST.
        All remote workers must have a stable internet connection (min 20 Mbps) and a dedicated workspace.
        
        Annual Leave Entitlement:
        - Full-time employees: 24 days per year
        - Probationary period (6 months): 12 days prorated
        - Sick leave: 10 days per year (non-cumulative)
        """
    },
    {
        "id": "doc_002",
        "source": "q3_financial_report.txt",
        "content": """
        TechCorp Q3 2024 Financial Summary
        
        Revenue: $142.3 million (up 18% YoY)
        Operating Expenses: $98.7 million
        Net Income: $43.6 million
        EBITDA Margin: 32.4%
        
        Key Highlights:
        - Cloud division revenue grew 42% to $67M, driven by enterprise AI products.
        - R&D spend increased to $22.1M (15.5% of revenue) reflecting AI-first strategy.
        - Headcount grew from 1,200 to 1,480 employees globally.
        - Customer churn rate dropped to 3.2% (from 5.1% in Q2).
        
        Guidance for Q4 2024:
        Revenue expected between $155M - $162M.
        Operating margin expected to improve by 1.5 percentage points.
        """
    },
    {
        "id": "doc_003",
        "source": "ai_product_specs.txt",
        "content": """
        TechCorp AI Platform — Technical Specifications v2.0
        
        Core Components:
        1. IntelliSearch Engine
           - Embedding Model: text-embedding-004 (768-dim vectors)
           - Vector Store: Pinecone (production), ChromaDB (dev/staging)
           - Retrieval Strategy: Hybrid (BM25 + Dense Retrieval), top-k=5
        
        2. Multi-Agent Orchestrator
           - Framework: LangGraph 0.1.x
           - Supported patterns: ReAct, CAMEL, Hierarchical Delegation
           - State persistence: Redis for session memory
        
        3. LLM Gateway
           - Primary: Gemini 1.5 Pro via Vertex AI
           - Fallback: Gemini 1.5 Flash for latency-sensitive tasks
           - Rate limits: 1,000 RPM per tenant, circuit-breaker enabled
        
        4. Observability
           - Tracing: OpenTelemetry + Jaeger
           - Metrics: Prometheus + Grafana dashboards
           - Alerting: PagerDuty for P0/P1 incidents (SLA: 99.9% uptime)
        
        Deployment:
        - Container: Docker (base: python:3.11-slim)
        - Orchestration: GCP Cloud Run (auto-scaling 1–50 instances)
        - CI/CD: GitHub Actions → Cloud Build → Artifact Registry
        """
    },
    {
        "id": "doc_004",
        "source": "security_policy.txt",
        "content": """
        TechCorp Information Security Policy — v3.1
        
        Data Classification:
        - Level 1 (Public): Marketing materials, public website content.
        - Level 2 (Internal): Internal wikis, general business docs.
        - Level 3 (Confidential): Customer PII, financial records, source code.
        - Level 4 (Restricted): Encryption keys, passwords, audit logs.
        
        Access Control:
        All Level 3+ data must follow the principle of least privilege.
        Access requests must be approved by the data owner + Security team.
        All privileged access is logged and reviewed monthly.
        
        Incident Response:
        - Detection to initial response: < 1 hour (P0 incidents)
        - Root cause analysis: within 48 hours of resolution
        - Customer notification: within 72 hours if PII is involved (GDPR-compliant)
        
        Encryption:
        - Data at rest: AES-256
        - Data in transit: TLS 1.3+
        - Key rotation: every 90 days via GCP Cloud KMS
        """
    },
    {
        "id": "doc_005",
        "source": "engineering_runbook.txt",
        "content": """
        SRE Runbook — AI Platform On-Call Guide
        
        Escalation Path:
        1. L1 Support (0-15 min): Check dashboards, verify service health.
        2. L2 On-Call Engineer (15-30 min): Deep-dive into logs, restart pods if needed.
        3. L3 Principal Engineer (30+ min): Architecture-level debugging.
        
        Common Issues & Resolutions:
        
        Issue: High Latency (>2000ms p99)
        - Check: Pinecone query latency, Vertex AI quota limits.
        - Fix: Enable Flash fallback; purge stale ChromaDB index shards.
        
        Issue: Vector Search returning irrelevant results
        - Check: Embedding model version mismatch.
        - Fix: Re-embed affected document collections with text-embedding-004.
        
        Issue: LangGraph agent stuck in infinite loop
        - Check: Recursion limit in graph config (default: 10).
        - Fix: Increase limit or add conditional break on iteration count.
        
        Deployment Checklist:
        [ ] All unit tests pass (pytest --cov > 85%)
        [ ] Integration tests pass against staging Chroma index
        [ ] Load test: 100 RPS for 5 minutes, p99 latency < 1500ms
        [ ] Security scan: no CRITICAL or HIGH vulnerabilities
        [ ] Rollback plan documented in Confluence
        """
    }
]
