"""Golden eval runner: drive the proposal harness across instances and score the proposals."""

from __future__ import annotations

from .report import summarize, write_results
from .runner import run_instances

__all__ = ["run_instances", "write_results", "summarize"]
