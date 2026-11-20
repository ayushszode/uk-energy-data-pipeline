"""Run the whole pipeline after extraction: load -> dbt build -> analysis -> forecast -> export.

    python -m energy_pipeline.pipeline            # uses the raw files already in data/raw
    python -m energy_pipeline.pipeline --extract  # download missing months first
"""
from __future__ import annotations

import argparse
import subprocess
import sys

from . import analysis, config, export, extract, forecast, load


def dbt(*args: str) -> None:
    cmd = ["dbt", *args, "--project-dir", "dbt", "--profiles-dir", "dbt"]
    print("[pipeline] " + " ".join(cmd))
    subprocess.run(cmd, cwd=config.ROOT, check=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--extract", action="store_true", help="download missing months before loading")
    ap.add_argument("--refresh-recent", type=int, default=0)
    args = ap.parse_args(argv)
    if args.extract:
        extract.main(["--refresh-recent", str(args.refresh_recent), "--end", "current"])
    load.load()
    dbt("build")
    dbt("docs", "generate")
    analysis.main()
    forecast.main()
    export.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
