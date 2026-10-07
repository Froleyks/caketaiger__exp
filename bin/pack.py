#!/usr/bin/env python3
"""Read benchmark data and benchmark files.

The data file must contain at least `dir`, `name`, and `time`.
Benchmark files end each task line with `@group dir name`.
"""
import os
import re

from sys import argv, exit

if len(argv) < 2:
    print("Usage: pack.py data [lists...] [--column <allowed values>] [--sub <seconds>] [--dry]")
    exit(1)
    
data = argv[1]
benchmarks = ['benchmarks']
filter = []
filter_le = []
sub = None
dry = False

parts = []
last = None
args = argv[2:] + ['--']
for i, a in enumerate(args):
    if a.startswith("--"):
        if last is None:
            benchmarks = args[:i]
        else:
            parts.append(args[last:i])
        last = i
for part in parts:
    key = part[0][2:]  # Remove "--"
    if key == "sub":
        if len(part) == 2:
            value = part[1]
        else:
            print("Usage: --sub <seconds>")
            exit(1)
        try:
            sub = float(value)
        except ValueError:
            print("Invalid subset time:", value)
            exit(1)
    elif key == "dry":
        if len(part) != 1:
            print("Usage: --dry")
            exit(1)
        dry = True
    elif len(part) < 2:
        print(f"Usage: --{key} <allowed values>")
        exit(1)
    elif part[1] == '=' and len(part) == 3:
        try:
            filter_le.append((key, float(part[2])))
        except ValueError:
            print("Invalid numeric bound:", part[2])
    else:
        filter.append((key, part[1:]))

for i in benchmarks + [data]:
    if not os.path.exists(i):
        print(f"File not found: {i}. Leaving benchmark files unchanged.")
        exit(0)

import pandas as pd

d = pd.read_csv(data)
columns = ['dir', 'name', 'time'] + [c for c, _ in filter] + [c for c, _ in filter_le]
for c in columns:
    if c not in d.columns:
        print(f"Error: column '{c}' not found in data")
        exit(1)
for c, values in filter:
    d = d[d[c].isin(values)]
for c, value in filter_le:
    d = d[d[c] <= value]
    
p = d.pivot(index="name", columns="dir", values="time")
p["max"] = p.max(axis=1)

TASK_LINE_RE = re.compile(
    r"^(?P<cmd>.*)@(?P<group>\S+)(?P<suffix>\s+(?P<dir>\S+)\s+(?P<name>.*?)(?P<newline>\n?))$"
)

lists = {benchmarks_file: [] for benchmarks_file in benchmarks}
for benchmarks_file in benchmarks:
    with open(benchmarks_file) as f:
        for line in f:
            match = TASK_LINE_RE.match(line)
            if not match:
                continue
            cmd = match.group("cmd")
            dir = match.group("dir")
            name = match.group("name")
            suffix = match.group("suffix")
            found = False
            if name not in p.index:
                t = float("inf")
            elif dir not in p.columns or pd.isna(p.loc[name, dir]):
                t = p.loc[name, "max"]
            else:
                t = p.loc[name, dir]
                found = True
            if (filter or filter_le) and not found:
                continue
            lists[benchmarks_file].append((t, benchmarks_file, cmd, suffix))
for benchmarks_file, entries in lists.items():
    entries.sort()

if sub is not None:
    total = 0.0
    limit = float("inf")
    times = sorted(
        entry[0]
        for benchmarks_file, entries in lists.items()
        for entry in entries
    )
    for t in times:
        if total + t > sub:
            limit = t
            break
        total += t
    print(f"sub {limit}")
    for benchmarks_file, entries in lists.items():
        lists[benchmarks_file] = [entry for entry in entries if entry[0] < limit]

def bin_pack(entries):
    short_limit = 5
    capacity = 60
    max_total = 0
    packed = []
    group = 0
    total = capacity
    for t, benchmarks_file, cmd, suffix in entries:
        if total >= capacity or t > short_limit:
            total = 0
            group += 1
        packed.append((t, benchmarks_file, cmd, suffix, group))
        total += t
        max_total = max(max_total, total)
    total_time = round(sum(e[0] for e in entries), 1)
    longest = round(max_total, 1)
    print(f"benchmarks: {len(entries):3}     groups: {group:3}    total: {total_time:7}s    longest: {longest:7}s")
    return packed

selected_rows = []
for benchmarks_file, entries in lists.items():
    dir = benchmarks_file.replace("benchmarks-", "")
    print(f"{dir:<16}", end="")
    packed = bin_pack(entries)
    if dry:
        for _, _, _, suffix, _ in packed:
            match = TASK_LINE_RE.match(f"@0{suffix}")
            if match:
                selected_rows.append((match.group("dir"), match.group("name")))
    else:
        with open(benchmarks_file, "w") as f:
            for t, benchmarks_file, cmd, suffix, group in packed:
                f.write(f"{cmd}@{group}{suffix}")

if dry:
    selected = pd.DataFrame(selected_rows, columns=["dir", "name"]).drop_duplicates()
    simulated = d.merge(selected, on=["dir", "name"], how="inner")
    simulated.to_csv(data + '-sub', index=False)
