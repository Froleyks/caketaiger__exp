#!/usr/bin/env python3
"""Collect compact logs with one read per file and C-backed byte searches."""
import csv
import os
import sys
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass


USAGE = """Usage:
  parse.py [--jobs N] [LOG_DIR ...] @ KEYWORD [COLUMN [INDEX] ...] ...

No directories means the current directory. Columns default to the keyword
without its trailing ':', and indices default to 1. Keywords are literal;
the last matching line and its last non-overlapping keyword occurrence win.
Missing values are NaN.
--jobs defaults to PARSE_JOBS (1); use small values to overlap file I/O.
"""


@dataclass(frozen=True)
class Spec:
    keyword: bytes
    column: str
    index: int


def decimal(value):
    return value.isascii() and value.isdecimal()


def arguments(args):
    dirs, specs = [], []
    jobs = os.environ.get("PARSE_JOBS", "1")
    i = 0
    while i < len(args) and args[i] != "@":
        arg = args[i]
        i += 1
        if arg in ("--help", "-h"):
            print(USAGE, end="")
            raise SystemExit(0)
        if arg in ("--jobs", "-j"):
            if i == len(args):
                raise ValueError("--jobs requires a positive integer")
            jobs = args[i]
            i += 1
        else:
            dirs.append(arg)
    if not decimal(jobs) or int(jobs) < 1:
        raise ValueError("--jobs / PARSE_JOBS must be a positive integer")

    while i < len(args):
        if args[i] != "@" or i + 1 == len(args) or not args[i + 1]:
            raise ValueError("each @ requires a nonempty keyword")
        keyword = args[i + 1]
        i += 2
        default = keyword.removesuffix(":")
        start = len(specs)
        while i < len(args) and args[i] != "@":
            column, index = default, 1
            if decimal(args[i]):
                index = int(args[i])
                i += 1
            else:
                column = args[i]
                i += 1
                if i < len(args) and decimal(args[i]):
                    index = int(args[i])
                    i += 1
            specs.append(Spec(os.fsencode(keyword), column, index))
        if len(specs) == start:
            specs.append(Spec(os.fsencode(keyword), default, 1))
    return dirs or [os.getcwd()], specs, int(jobs)


def last_tail(data, keyword):
    """Search in native code; tokenize only the final matching line.

    Checking the chosen line forwards preserves the old parser's non-overlap
    rule even for keywords such as 'aa' in 'aaa 1'.
    """
    pos = data.rfind(keyword)
    if pos < 0:
        return None
    start = data.rfind(b"\n", 0, pos) + 1
    end = data.find(b"\n", pos)
    if end < 0:
        end = len(data)
    match = data.find(keyword, start, end)
    if match < 0:
        return None
    while match >= 0:
        pos = match
        match = data.find(keyword, pos + len(keyword), end)
    tail = data[pos + len(keyword):end]
    return tail[1:] if tail.startswith(b":") else tail


def words(data, keyword):
    tail = last_tail(data, keyword)
    return [] if tail is None else tail.split()


def log_paths(dirs):
    for directory in dirs:
        try:
            with os.scandir(directory) as entries:
                paths = [entry.path for entry in entries
                         if not entry.name.startswith(".")
                         and entry.name.endswith(".log") and entry.is_file()]
        except (FileNotFoundError, NotADirectoryError):
            continue
        yield from sorted(paths)


def identity(path):
    directory = os.path.basename(os.path.normpath(os.path.dirname(path)))
    directory = directory.removeprefix("log-").removesuffix("-all").removesuffix("-smoketest").removesuffix("-sub")
    name = os.path.basename(path).removesuffix(".log").removeprefix(directory + "_")
    return [directory, name]


def ordered_rows(paths, parse, jobs):
    if jobs == 1:
        for path in paths:
            yield parse(path)
        return
    # Bounded submission keeps only a small number of logs/results in memory,
    # even when the first read is slow. Preserve directory and filename order.
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        pending = deque()
        for path in paths:
            pending.append(pool.submit(parse, path))
            if len(pending) >= jobs * 2:
                yield pending.popleft().result()
        while pending:
            yield pending.popleft().result()


def main(args):
    dirs, specs, jobs = arguments(args)
    # Search each distinct keyword once, including multi-column specifications.
    keywords = dict.fromkeys(spec.keyword for spec in specs)

    def parse(path):
        with open(path, "rb") as source:
            data = source.read()
        values = {key: words(data, key) for key in keywords}
        row = identity(path)
        for spec in specs:
            tokens = values[spec.keyword]
            row.append(os.fsdecode(tokens[spec.index - 1])
                       if 1 <= spec.index <= len(tokens) else "NaN")
        return row

    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(["dir", "name"] + [spec.column for spec in specs])
    writer.writerows(ordered_rows(log_paths(dirs), parse, jobs))


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except (OSError, ValueError) as error:
        print(f"parse.py: {error}", file=sys.stderr)
        sys.exit(1)
