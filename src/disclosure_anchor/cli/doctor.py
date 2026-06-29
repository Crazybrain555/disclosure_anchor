"""CLI for Phase 01 doctor checks."""

from __future__ import annotations

import sys

from pydantic import ValidationError

from disclosure_anchor.adapters.runtime.doctor import render_report, run_doctor
from disclosure_anchor.settings import load_settings


def main() -> int:
    try:
        settings = load_settings()
    except ValidationError as exc:
        print(f"[FAIL] settings: {exc}", file=sys.stderr)
        return 2

    report = run_doctor(settings)
    print(render_report(report.results))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
