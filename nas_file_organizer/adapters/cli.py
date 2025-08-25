from __future__ import annotations
from pathlib import Path
from rich.console import Console
from ..core.services import OrganizerService

def main():
    console = Console()
    svc = OrganizerService()
    opts = svc.load_options(Path("rules.yaml"))

    console.rule("[bold green]Plan")
    planned = list(svc.plan(opts))
    for r in planned[:50]:
        if r.dst:
            console.print(f"[cyan]{r.src.name}[/] -> [green]{r.dst}[/]  (rule: {r.rule})")
        else:
            console.print(f"[yellow]{r.src.name}[/] -> [dim]no match[/]")

    if console.input("\nProceed (y/N)? ").strip().lower() == "y":
        console.rule("[bold green]Execute")
        opts.dry_run = False
        for r in svc.execute(opts):
            if r.ok and r.dst:
                console.print(f"[green]Moved:[/] {r.src.name} -> {r.dst.name}")
            elif r.reason == "no_match":
                console.print(f"[yellow]Skipped:[/] {r.src.name} (no match)")
            else:
                console.print(f"[red]Error:[/] {r.src.name} -> {r.reason}")

if __name__ == "__main__":
    main()
