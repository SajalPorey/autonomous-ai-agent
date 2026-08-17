import sys
import argparse
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

load_dotenv()

from app.models.task import GoalRequest
from app.agent.executor import SazonExecutor
from app.agent.tools import default_registry

console = Console()


def print_banner():
    banner_text = """
 [bold cyan]SAZON AUTONOMOUS AI AGENT[/bold cyan]
 [dim]Goal-Driven Task Planning & Execution Engine[/dim]
    """
    console.print(Panel(banner_text, border_style="cyan"))


def display_result(result):
    console.print("\n[bold green]Goal Execution Finished![/bold green]")
    console.print(f"Goal: [italic]{result.goal}[/italic]")
    console.print(f"Total Iterations: {result.total_iterations} | Time: {result.execution_time_seconds}s\n")

    # Display Tasks Table
    table = Table(title="Subtasks Execution Plan", border_style="blue")
    table.add_column("ID", style="dim", width=10)
    table.add_column("Title", style="bold")
    table.add_column("Tool", style="magenta")
    table.add_column("Status", style="green")

    for task in result.tasks:
        status_val = task.status.value if hasattr(task.status, "value") else str(task.status)
        status_color = "green" if status_val == "completed" else "yellow"
        table.add_row(
            task.id,
            task.title,
            task.tool_name or "None",
            f"[{status_color}]{status_val}[/{status_color}]"
        )

    console.print(table)

    # Display Final Answer Panel
    console.print("\n", Panel(result.final_answer, title="[bold green]Final Outcome[/bold green]", border_style="green"))


def run_single_goal(goal: str, max_iterations: int = 10):
    console.print(f"\n[bold yellow]Initializing Sazon for goal:[/bold yellow] {goal}")
    req = GoalRequest(goal=goal, max_iterations=max_iterations)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Sazon is planning and executing...", total=None)
        executor = SazonExecutor(req)
        result = executor.run()

    display_result(result)


def interactive_mode():
    print_banner()
    console.print("[dim]Type your goal and press Enter. Type 'exit' or 'quit' to exit.[/dim]\n")

    while True:
        try:
            goal = console.input("[bold cyan]Sazon>[/bold cyan] ").strip()
            if not goal:
                continue
            if goal.lower() in ("exit", "quit", "q"):
                console.print("[yellow]Goodbye![/yellow]")
                break
            if goal.lower() == "tools":
                tools = default_registry.list_tools()
                table = Table(title="Available Tools")
                table.add_column("Tool Name", style="cyan")
                table.add_column("Description")
                for t in tools:
                    table.add_row(t["name"], t["description"])
                console.print(table)
                continue

            run_single_goal(goal)
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Exiting Sazon.[/yellow]")
            break


def main():
    parser = argparse.ArgumentParser(description="Sazon Autonomous AI Agent CLI")
    parser.add_argument("goal", nargs="?", type=str, help="Goal for Sazon to execute")
    parser.add_argument("--iterations", type=int, default=10, help="Max iterations")
    args = parser.parse_args()

    if args.goal:
        print_banner()
        run_single_goal(args.goal, max_iterations=args.iterations)
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
