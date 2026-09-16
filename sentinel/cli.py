"""
CLI:
  sentinel simulate --world worlds/exposure.json --budgets 2 5 10 --ticks 200 --seeds 20 --out reports/exposure.md
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Sequence

from .simulate import render, sweep
from .world import WorldSpec


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="sentinel", description="Verification scheduling under freshness decay (simulation only).")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("simulate", help="run every policy on a world across budgets and seeds; write a report")
    s.add_argument("--world", required=True)
    s.add_argument("--budgets", type=float, nargs="+", default=[2.0, 5.0, 10.0])
    s.add_argument("--ticks", type=int, default=200)
    s.add_argument("--seeds", type=int, default=20)
    s.add_argument("--out", required=True)
    s.add_argument("--json", dest="json_path")
    args = p.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    spec = WorldSpec.load(args.world)
    seeds = list(range(1, args.seeds + 1))
    results = sweep(spec, seeds=seeds, ticks=args.ticks, budgets=args.budgets)
    command = (f"sentinel simulate --world {args.world} --budgets {' '.join(f'{b:g}' for b in args.budgets)} "
               f"--ticks {args.ticks} --seeds {args.seeds} --out {args.out}")
    text = render(spec, results, seeds, args.ticks, command)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_bytes(text.encode("utf-8"))
    if args.json_path:
        Path(args.json_path).write_bytes(json.dumps({str(k): v for k, v in results.items()}, indent=2).encode("utf-8"))
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
