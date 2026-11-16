import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class AgentSpan:
    agent_name: str
    action: str
    start_time: float
    end_time: float = 0.0
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    status: str = "running"
    details: Dict[str, Any] = field(default_factory=dict)

    def finish(self, input_tokens: int = 0, output_tokens: int = 0, details: Optional[Dict[str, Any]] = None):
        self.end_time = time.perf_counter()
        self.latency_ms = round((self.end_time - self.start_time) * 1000, 2)
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.status = "completed"
        
        # Standard estimation: Gemini 1.5 Flash ~$0.075 / 1M input, $0.30 / 1M output
        input_cost = (input_tokens / 1_000_000) * 0.075
        output_cost = (output_tokens / 1_000_000) * 0.30
        self.estimated_cost_usd = round(input_cost + output_cost, 6)
        
        if details:
            self.details.update(details)


class TelemetryTracker:
    """
    Tracks LLM-native metrics requested in the Google JD:
    - Tokens per second (throughput)
    - Cost per request (economics)
    - Granular state tracing & latency per agent span
    """
    def __init__(self, trace_id: str = ""):
        self.trace_id = trace_id or str(int(time.time() * 1000))
        self.spans: List[AgentSpan] = []
        self.start_time = time.perf_counter()
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    def start_span(self, agent_name: str, action: str) -> AgentSpan:
        span = AgentSpan(
            agent_name=agent_name,
            action=action,
            start_time=time.perf_counter()
        )
        self.spans.append(span)
        return span

    def record_usage(self, input_tokens: int, output_tokens: int):
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

    def get_summary(self) -> Dict[str, Any]:
        total_time_sec = max(time.perf_counter() - self.start_time, 0.001)
        total_tokens = self.total_input_tokens + self.total_output_tokens
        tokens_per_sec = round(self.total_output_tokens / total_time_sec, 2)
        total_cost = sum(span.estimated_cost_usd for span in self.spans)

        return {
            "trace_id": self.trace_id,
            "total_latency_ms": round(total_time_sec * 1000, 2),
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "tokens_per_sec": tokens_per_sec,
            "total_cost_usd": round(total_cost, 6),
            "span_count": len(self.spans),
            "spans": [
                {
                    "agent": s.agent_name,
                    "action": s.action,
                    "latency_ms": s.latency_ms,
                    "input_tokens": s.input_tokens,
                    "output_tokens": s.output_tokens,
                    "cost_usd": s.estimated_cost_usd,
                    "status": s.status,
                    "details": s.details,
                }
                for s in self.spans
            ]
        }
