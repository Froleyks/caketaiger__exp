#!/usr/bin/env python3
"""Select the HWMCC certificates that `sub` checks one at a time.

Usage: sequential.py data --time T --check S --budget B lists...

Each `benchmarks-<config>-sub-seq` list is reduced to certificates absent from
the parallel `benchmarks-<config>-sub` lists that every configuration
validates within T seconds in `data` and default Certifaiger checks for at
least S seconds, cheapest first while the reference wall times summed over all
configurations fit into B seconds.
Selected lines check the certificate conditions sequentially to bound memory.
"""
import argparse
import re
from pathlib import Path

import pandas as pd

BASELINE = "certifaiger"
TASK_LINE_RE = re.compile(r"^(?P<cmd>.*)@(?P<group>\S+)\s+(?P<dir>\S+)\s+(?P<name>.*?)\n?$")

parser = argparse.ArgumentParser()
parser.add_argument("data")
parser.add_argument("lists", nargs="+")
parser.add_argument("--time", type=float, required=True)
parser.add_argument("--check", type=float, required=True)
parser.add_argument("--budget", type=float, required=True)
args = parser.parse_args()


def entries(path):
    if not Path(path).exists():
        return []
    with open(path) as f:
        return [m for m in map(TASK_LINE_RE.match, f) if m]


lists = {path: entries(path) for path in args.lists}
parallel = {m["name"] for path in args.lists for m in entries(path.removesuffix("-seq"))}
dirs = sorted({m["dir"] for ms in lists.values() for m in ms})

d = pd.read_csv(args.data)
d = d[d.dir.isin(dirs)]
d["check"] = d.filter(regex="^check_").sum(axis=1)
d["combined"] = d.filter(regex="^(generation$|split$|cnf_|check_)").sum(axis=1)
d["ok"] = (d.status == "ok") & (d.time <= args.time) & (d.combined <= args.time)
d["cost"] = d.time.where(d.ok, args.time).clip(upper=args.time)
ok = d.pivot(index="name", columns="dir", values="ok").reindex(columns=dirs)
measured = ok.notna().all(axis=1) & ~ok.index.isin(parallel)
ok = ok.eq(True)
cost = d.pivot(index="name", columns="dir", values="cost").sum(axis=1)
check = d.pivot(index="name", columns="dir", values="check")[BASELINE]

hard = cost[measured & ok.all(axis=1) & (check >= args.check)].sort_values(kind="stable")
hard = hard[hard.cumsum() <= args.budget]
selected = set(hard.index)
print(f"sequential: {len(hard)} certificates ({hard.sum():.0f}s reference wall time)")

for path, ms in lists.items():
    with open(path, "w") as f:
        for m in ms:
            if m["name"] in selected:
                f.write(f"SEQUENTIAL=true {m['cmd']}@{m['group']} {m['dir']} {m['name']}\n")
