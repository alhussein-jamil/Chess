"""Rich logging helpers."""

from __future__ import annotations

import logging
from collections.abc import Iterable

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TransferSpeedColumn,
)
from rich.rule import Rule
from rich.table import Table

_console = Console()
_configured = False


def setup_logging(level: str = "INFO", show_path: bool = False) -> None:
    global _configured
    numeric = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=_console, show_path=show_path, markup=True)],
        force=True,
    )
    for name in ("urllib3", "PIL"):
        logging.getLogger(name).setLevel(logging.WARNING)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    if not _configured:
        setup_logging()
    return logging.getLogger(name)


def log_banner(command: str) -> None:
    _console.print(Panel(f"[bold]chess[/bold] — {command}", border_style="cyan"))


def log_rule(title: str) -> None:
    _console.print(Rule(title, style="dim"))


def log_kv_table(title: str, rows: Iterable[tuple[str, str]]) -> None:
    table = Table(title=title, show_header=True, header_style="bold")
    table.add_column("Key", style="cyan")
    table.add_column("Value")
    for key, value in rows:
        table.add_row(key, value)
    _console.print(table)


def download_progress() -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeElapsedColumn(),
        console=_console,
    )


def task_progress(description: str = "Working") -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=_console,
    )
