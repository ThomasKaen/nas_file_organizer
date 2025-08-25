from __future__ import annotations
import argparse
from pathlib import Path
from rich.console import Console
from ..core.services import OrganizerService

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="nas-organize", description="NAS File Organizer")
    p.add_argument("-c", "--config", default="rules.yaml", help="Path to rules.yaml")
    p.add_argument("--execute", action="store_true", help="Execute moves (otherwise plan only)")
    p.add_argument("--dry-run", type=str, choices=["true","false"], help="Override dry_run from config")
    return p.parse_args()

def main():
    args = parse_args()
    console = Console()
    svc = OrganizerService()
    cfg_path = Path(args.config)
    opts = svc.load_options(cfg_path)
    if args.dry_run is not None:
        opts.dry_run = (args.dry_run.lower() == "true")

    console.rule(f"[bold green]Plan ({cfg_path})")
    planned = list(svc.plan(opts))
    for r in planned[:200]:
        if r.dst:
            console.print(f"[cyan]{r.src.name}[/] -> [green]{r.dst}[/]  (rule: {r.rule})")
        else:
            console.print(f"[yellow]{r.src.name}[/] -> [dim]no match[/]")

    if args.execute or (console.input("\nProceed (y/N)? ").strip().lower() == "y"):
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
