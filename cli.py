"""
Interactive CLI playground for the Enterprise Multi-Agent RAG System.
Provides a rich terminal interface with colored output and telemetry display.
"""

import os
import sys
import json
from dotenv import load_dotenv

load_dotenv()

# Force UTF-8 output on Windows to prevent emoji encode errors
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(__file__))

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.rule import Rule
    from rich import print as rprint
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from src.agents.workflow import run_query, LANGGRAPH_AVAILABLE
from src.storage.vector_store import VectorStore


console = Console() if RICH_AVAILABLE else None

SAMPLE_QUERIES = [
    "What is the remote work policy at TechCorp?",
    "Who are the top 3 highest-paid employees?",
    "What are the security classification levels for data?",
    "Show me all Q3-2024 sales deals and their values.",
    "What is the deployment checklist from the SRE runbook?",
    "What was TechCorp's revenue and net income in Q3 2024?",
    "List all active engineering projects and their budgets.",
]


def print_header():
    if RICH_AVAILABLE:
        console.print(Panel.fit(
            "[bold blue]Enterprise Hierarchical Multi-Agent RAG System[/]\n"
            "[dim]LangGraph · ChromaDB · SQL · Telemetry Tracing[/]\n"
            f"[dim]LangGraph: {'[OK] Available' if LANGGRAPH_AVAILABLE else '[!] Fallback mode'}[/]",
            border_style="blue"
        ))
    else:
        print("=" * 60)
        print("Enterprise Hierarchical Multi-Agent RAG System")
        print("=" * 60)


def print_result(result: dict):
    if RICH_AVAILABLE:
        # Answer panel
        console.print(Panel(
            result.get("final_answer", "No answer."),
            title=f"[bold green]ANSWER[/] [dim](Route: {result.get('route', '?')} | Iterations: {result.get('iteration', 0)})[/]",
            border_style="green"
        ))

        # Citations
        citations = result.get("citations", [])
        if citations:
            console.print(f"[dim]Sources: {' · '.join(citations)}[/]")

        # Grading
        rel = result.get("relevance_grade", "N/A")
        hal = result.get("hallucination_grade", "N/A")
        rel_color = "green" if rel == "relevant" else "red"
        hal_color = "green" if hal == "grounded" else "red"
        console.print(
            f"[dim]Relevance: [{rel_color}]{rel}[/]  "
            f"Hallucination: [{hal_color}]{hal}[/][/]"
        )

        # Telemetry table
        tel = result.get("telemetry", {})
        if tel:
            table = Table(title="LLM Telemetry", show_header=True, header_style="bold magenta")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="yellow")
            table.add_row("Total Latency", f"{tel.get('total_latency_ms', 0):.1f} ms")
            table.add_row("Output Tokens/sec", str(tel.get("tokens_per_sec", 0)))
            table.add_row("Input Tokens", str(tel.get("total_input_tokens", 0)))
            table.add_row("Output Tokens", str(tel.get("total_output_tokens", 0)))
            table.add_row("Estimated Cost", f"${tel.get('total_cost_usd', 0):.6f}")
            table.add_row("Agent Spans", str(tel.get("span_count", 0)))
            console.print(table)

            # Span details
            spans = tel.get("spans", [])
            if spans:
                console.print("[dim]Agent execution trace:[/]")
                for s in spans:
                    console.print(
                        f"  [cyan]{s['agent']}[/] -> [yellow]{s['action']}[/] "
                        f"[dim]{s['latency_ms']}ms | {s['output_tokens']} tokens[/]"
                    )
    else:
        print(f"\n--- ANSWER ({result.get('route', '?')}) ---")
        print(result.get("final_answer", "No answer."))
        tel = result.get("telemetry", {})
        if tel:
            print(f"\n--- TELEMETRY ---")
            print(f"Latency: {tel.get('total_latency_ms', 0):.1f}ms | "
                  f"Tokens/sec: {tel.get('tokens_per_sec', 0)} | "
                  f"Cost: ${tel.get('total_cost_usd', 0):.6f}")


def run_demo_mode():
    """Run all sample queries in sequence to demonstrate the system."""
    print_header()
    if RICH_AVAILABLE:
        console.print("\n[bold yellow]Running DEMO mode with sample queries...[/]\n")

    for i, query in enumerate(SAMPLE_QUERIES, 1):
        if RICH_AVAILABLE:
            console.rule(f"[bold]Query {i}/{len(SAMPLE_QUERIES)}[/]")
            console.print(f"[bold white]Q: {query}[/]\n")
        else:
            print(f"\n{'='*50}\nQuery {i}: {query}\n")

        try:
            result = run_query(query)
            print_result(result)
        except Exception as e:
            if RICH_AVAILABLE:
                console.print(f"[red]Error: {e}[/]")
            else:
                print(f"Error: {e}")

        if RICH_AVAILABLE:
            console.print()


def run_interactive_mode():
    """Interactive REPL for querying the system."""
    print_header()

    # Ensure documents are indexed
    vs = VectorStore()
    count = vs.ingest_documents()
    if RICH_AVAILABLE:
        console.print(f"\n[dim]📂 Vector store ready. Documents indexed: {vs.count()}[/]\n")
        console.print("[dim]Type a question or 'demo' to run sample queries. 'quit' to exit.[/]\n")

    while True:
        try:
            if RICH_AVAILABLE:
                query = console.input("[bold cyan]❓ Your query: [/]").strip()
            else:
                query = input("Your query: ").strip()
        except (KeyboardInterrupt, EOFError):
            if RICH_AVAILABLE:
                console.print("\n[dim]Exiting. Goodbye![/]")
            break

        if not query:
            continue
        if query.lower() in ("quit", "exit", "q"):
            break
        if query.lower() == "demo":
            run_demo_mode()
            continue

        if RICH_AVAILABLE:
            console.print("[dim]Processing...[/]")
        try:
            result = run_query(query)
            print_result(result)
        except Exception as e:
            if RICH_AVAILABLE:
                console.print(f"[red]Pipeline error: {e}[/]")
            else:
                print(f"Error: {e}")

        if RICH_AVAILABLE:
            console.print()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Enterprise Multi-Agent RAG CLI")
    parser.add_argument("--demo", action="store_true", help="Run demo mode with sample queries")
    parser.add_argument("--query", "-q", type=str, help="Run a single query and exit")
    args = parser.parse_args()

    if args.query:
        print_header()
        result = run_query(args.query)
        print_result(result)
    elif args.demo:
        run_demo_mode()
    else:
        run_interactive_mode()
