"""Golden-set eval / scoreboard pipeline."""

from __future__ import annotations

from app.eval.load import default_golden_path, default_report_path, load_golden
from app.eval.run import run_eval

__all__ = [
    "default_golden_path",
    "default_report_path",
    "load_golden",
    "run_eval",
]
