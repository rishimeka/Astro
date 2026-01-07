"""Sidekick CLI for viewing execution traces.

Provides command-line interface for querying and viewing traces.
"""

import asyncio
import json
from typing import Optional
import sys

# Try to import click and rich
try:
    import click

    CLICK_AVAILABLE = True
except ImportError:
    click = None
    CLICK_AVAILABLE = False

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.tree import Tree

    RICH_AVAILABLE = True
except ImportError:
    Console = None
    Table = None
    Panel = None
    Tree = None
    RICH_AVAILABLE = False

from sidekick.persistence import SidekickPersistence
from sidekick.config import get_config


def create_console():
    """Create Rich console if available."""
    if RICH_AVAILABLE:
        return Console()
    return None


console = create_console()


def print_output(text: str, style: str = None):
    """Print output using Rich if available, otherwise plain print."""
    if console and style:
        console.print(text, style=style)
    elif console:
        console.print(text)
    else:
        print(text)


def print_error(text: str):
    """Print error message."""
    if console:
        console.print(f"[red]Error: {text}[/red]")
    else:
        print(f"Error: {text}", file=sys.stderr)


if CLICK_AVAILABLE:

    @click.group()
    def cli():
        """Sidekick CLI for viewing execution traces."""
        pass

    @cli.command()
    @click.option("--limit", default=10, help="Number of traces to show")
    @click.option(
        "--status", default=None, help="Filter by status (completed, failed, running)"
    )
    def list(limit: int, status: Optional[str]):
        """List recent execution traces."""
        persistence = SidekickPersistence()

        async def _list():
            return await persistence.get_recent_traces(limit=limit, status=status)

        traces = asyncio.run(_list())

        if not traces:
            print_output("No traces found.", style="yellow")
            return

        if RICH_AVAILABLE:
            table = Table(title="Recent Traces")
            table.add_column("Trace ID", style="cyan", width=12)
            table.add_column("Query", style="white", width=40)
            table.add_column("Status", style="green")
            table.add_column("Duration", style="yellow")
            table.add_column("Workers", style="blue")
            table.add_column("LLM Calls", style="magenta")

            for trace in traces:
                query = (
                    trace.original_query[:40] + "..."
                    if len(trace.original_query) > 40
                    else trace.original_query
                )
                status_style = (
                    "green"
                    if trace.status == "completed"
                    else "red" if trace.status == "failed" else "yellow"
                )
                table.add_row(
                    trace.trace_id[:12],
                    query,
                    f"[{status_style}]{trace.status}[/{status_style}]",
                    f"{trace.total_duration_seconds:.1f}s",
                    str(trace.total_workers),
                    str(trace.total_llm_calls),
                )

            console.print(table)
        else:
            print("\nRecent Traces:")
            print("-" * 80)
            for trace in traces:
                query = (
                    trace.original_query[:40] + "..."
                    if len(trace.original_query) > 40
                    else trace.original_query
                )
                print(f"ID: {trace.trace_id[:12]}")
                print(f"  Query: {query}")
                print(f"  Status: {trace.status}")
                print(f"  Duration: {trace.total_duration_seconds:.1f}s")
                print(f"  Workers: {trace.total_workers}")
                print()

    @cli.command()
    @click.argument("trace_id")
    def show(trace_id: str):
        """Show details for a specific trace."""
        persistence = SidekickPersistence()

        async def _get():
            return await persistence.get_trace(trace_id)

        trace = asyncio.run(_get())

        if not trace:
            print_error(f"Trace {trace_id} not found")
            return

        if RICH_AVAILABLE:
            # Header
            status_color = (
                "green"
                if trace.status == "completed"
                else "red" if trace.status == "failed" else "yellow"
            )
            console.print(
                Panel(
                    f"[bold]Trace: {trace.trace_id}[/bold]\n\n"
                    f"[bold]Query:[/bold] {trace.original_query}\n"
                    f"[bold]Status:[/bold] [{status_color}]{trace.status}[/{status_color}]\n"
                    f"[bold]Duration:[/bold] {trace.total_duration_seconds:.2f}s\n"
                    f"[bold]LLM Calls:[/bold] {trace.total_llm_calls}\n"
                    f"[bold]Tool Calls:[/bold] {trace.total_tool_calls}",
                    title="Execution Trace",
                )
            )

            if trace.error:
                console.print(f"\n[red]Error: {trace.error}[/red]")

            # Stars used
            if trace.stars_used:
                console.print("\n[bold]Stars Used:[/bold]")
                for star_id, version in trace.stars_used.items():
                    console.print(f"  - {star_id}: v{version}")

            # Phases
            for phase in trace.phases:
                phase_color = (
                    "green"
                    if phase.status == "completed"
                    else "red" if phase.status == "failed" else "yellow"
                )
                console.print(
                    f"\n[bold cyan]Phase {phase.phase_index}: {phase.phase_name}[/bold cyan]"
                )
                console.print(
                    f"  Status: [{phase_color}]{phase.status}[/{phase_color}]"
                )
                console.print(f"  Duration: {phase.duration_seconds:.2f}s")
                console.print(
                    f"  Workers: {phase.workers_completed} completed, {phase.workers_failed} failed"
                )

                if phase.error:
                    console.print(f"  [red]Error: {phase.error}[/red]")

                for worker in phase.workers:
                    worker_color = "green" if worker.status == "completed" else "red"
                    console.print(
                        f"\n    [{worker_color}]Worker: {worker.worker_name}[/{worker_color}]"
                    )
                    console.print(
                        f"      Star: {worker.star_id} (v{worker.star_version})"
                    )
                    console.print(f"      Iterations: {worker.total_iterations}")
                    console.print(f"      Tool calls: {worker.total_tool_calls}")
                    console.print(f"      Duration: {worker.duration_seconds:.2f}s")

                    if worker.error:
                        console.print(f"      [red]Error: {worker.error}[/red]")

                    if worker.final_output:
                        output = (
                            worker.final_output[:200] + "..."
                            if len(worker.final_output) > 200
                            else worker.final_output
                        )
                        console.print(f"      Output: {output}")
        else:
            print(f"\nTrace: {trace.trace_id}")
            print(f"Query: {trace.original_query}")
            print(f"Status: {trace.status}")
            print(f"Duration: {trace.total_duration_seconds:.2f}s")
            print(f"LLM Calls: {trace.total_llm_calls}")
            print(f"Tool Calls: {trace.total_tool_calls}")

            if trace.error:
                print(f"Error: {trace.error}")

            for phase in trace.phases:
                print(f"\nPhase {phase.phase_index}: {phase.phase_name}")
                print(f"  Status: {phase.status}")
                print(f"  Duration: {phase.duration_seconds:.2f}s")

                for worker in phase.workers:
                    print(f"\n    Worker: {worker.worker_name}")
                    print(f"      Status: {worker.status}")
                    print(f"      Iterations: {worker.total_iterations}")

    @cli.command()
    @click.argument("trace_id")
    @click.argument("output_file")
    def export(trace_id: str, output_file: str):
        """Export a trace to JSON for Nebula."""
        persistence = SidekickPersistence()

        async def _get():
            return await persistence.get_traces_for_nebula(trace_id)

        result = asyncio.run(_get())

        if not result:
            print_error(f"Trace {trace_id} not found")
            return

        with open(output_file, "w") as f:
            json.dump(result, f, indent=2, default=str)

        print_output(f"Exported to {output_file}", style="green")

    @cli.command()
    def stats():
        """Show trace statistics."""
        persistence = SidekickPersistence()

        async def _stats():
            total = await persistence.count_traces()
            completed = await persistence.count_traces(status="completed")
            failed = await persistence.count_traces(status="failed")
            running = await persistence.count_traces(status="running")
            return total, completed, failed, running

        total, completed, failed, running = asyncio.run(_stats())

        if RICH_AVAILABLE:
            table = Table(title="Trace Statistics")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="white")

            table.add_row("Total Traces", str(total))
            table.add_row("Completed", f"[green]{completed}[/green]")
            table.add_row("Failed", f"[red]{failed}[/red]")
            table.add_row("Running", f"[yellow]{running}[/yellow]")
            if total > 0:
                table.add_row("Success Rate", f"{completed / total * 100:.1f}%")

            console.print(table)
        else:
            print("\nTrace Statistics:")
            print(f"  Total: {total}")
            print(f"  Completed: {completed}")
            print(f"  Failed: {failed}")
            print(f"  Running: {running}")
            if total > 0:
                print(f"  Success Rate: {completed / total * 100:.1f}%")

    @cli.command()
    @click.confirmation_option(prompt="Are you sure you want to cleanup old traces?")
    def cleanup():
        """Delete traces older than retention period."""
        persistence = SidekickPersistence()
        config = get_config()

        async def _cleanup():
            return await persistence.cleanup_old_traces()

        deleted = asyncio.run(_cleanup())

        print_output(
            f"Deleted {deleted} traces older than {config.trace_retention_days} days",
            style="green",
        )

    @cli.command()
    @click.option("--query", "-q", help="Search query")
    @click.option("--status", "-s", help="Filter by status")
    @click.option("--limit", "-l", default=10, help="Max results")
    def search(query: Optional[str], status: Optional[str], limit: int):
        """Search traces."""
        persistence = SidekickPersistence()

        async def _search():
            return await persistence.search_traces(
                query_text=query,
                status=status,
                limit=limit,
            )

        traces = asyncio.run(_search())

        if not traces:
            print_output("No matching traces found.", style="yellow")
            return

        if RICH_AVAILABLE:
            table = Table(title=f"Search Results ({len(traces)} found)")
            table.add_column("Trace ID", style="cyan", width=12)
            table.add_column("Query", style="white", width=40)
            table.add_column("Status", style="green")
            table.add_column("Duration", style="yellow")

            for trace in traces:
                query_text = (
                    trace.original_query[:40] + "..."
                    if len(trace.original_query) > 40
                    else trace.original_query
                )
                status_style = (
                    "green"
                    if trace.status == "completed"
                    else "red" if trace.status == "failed" else "yellow"
                )
                table.add_row(
                    trace.trace_id[:12],
                    query_text,
                    f"[{status_style}]{trace.status}[/{status_style}]",
                    f"{trace.total_duration_seconds:.1f}s",
                )

            console.print(table)
        else:
            print(f"\nSearch Results ({len(traces)} found):")
            for trace in traces:
                print(f"  {trace.trace_id[:12]}: {trace.original_query[:50]}...")


def main():
    """Main entry point for CLI."""
    if not CLICK_AVAILABLE:
        print("Error: click not installed. Run: pip install click")
        sys.exit(1)

    cli()


if __name__ == "__main__":
    main()
