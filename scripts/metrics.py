#!/usr/bin/env python3
"""WarpOne metrics helper — parse logs -> summary.json -> METRICS.md row.

Phase 0: scaffold. `summarize` collects whatever signals exist (git commit, date,
phase) into summary.json; `append-row` turns a summary.json into an appended row in
METRICS.md (append-only — never rewrites existing rows, standard #9/#10). Per-block
flop counts, coverage %, WNS, and ATPG % are filled in as those phases produce them.
"""
import argparse
import datetime
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def git_commit():
    try:
        return subprocess.check_output(
            ["git", "-C", ROOT, "rev-parse", "--short", "HEAD"],
            text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:  # noqa: BLE001
        return "(uncommitted)"


def summarize(args):
    summary = {
        "date": datetime.date.today().isoformat(),
        "commit": git_commit(),
        "phase": args.phase,
        "fuzz": args.fuzz or "—",
        "cov": args.cov or "—",
        "flops": args.flops or "—",
        "wns": args.wns or "—",
        "atpg": args.atpg or "—",
        "notes": args.notes or "",
    }
    out = os.path.join(ROOT, "summary.json")
    with open(out, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"wrote {out}")
    print(json.dumps(summary, indent=2))
    return 0


def append_row(args):
    with open(args.summary) as f:
        s = json.load(f)
    row = "| {date} | {commit} | {phase} | {fuzz} | {cov} | {flops} | {wns} | {atpg} | {notes} |".format(**s)
    metrics = os.path.join(ROOT, "METRICS.md")
    with open(metrics, "a") as f:
        f.write(row + "\n")
    print("appended to METRICS.md:\n" + row)
    return 0


def main():
    p = argparse.ArgumentParser(description="WarpOne metrics helper")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("summarize", help="emit summary.json")
    s.add_argument("--phase", required=True)
    s.add_argument("--fuzz")
    s.add_argument("--cov")
    s.add_argument("--flops")
    s.add_argument("--wns")
    s.add_argument("--atpg")
    s.add_argument("--notes")
    s.set_defaults(func=summarize)

    a = sub.add_parser("append-row", help="append summary.json as a METRICS.md row")
    a.add_argument("--summary", default=os.path.join(ROOT, "summary.json"))
    a.set_defaults(func=append_row)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
