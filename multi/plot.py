#!/usr/bin/env python3
"""Model sizes and Caketiger witness timings, sorted by checking time."""
from pathlib import Path
from sys import argv
import pandas as pd

src, out = argv[1:]
d = pd.read_csv(src)
d["Generation (s)"] = d.generation
d["Checking (s)"] = d.filter(regex="^check_").sum(axis=1, min_count=1)

d["witness"] = d.name.str.split("-", n=1).str[1]
d["total"] = d["Generation (s)"] + d["Checking (s)"]
hard = d.groupby("witness")["total"].transform("max") > 5
if hard.any():
    d = d[hard].copy()
d["max_check"] = d.groupby("witness")["Checking (s)"].transform("max")
d["engine_order"] = d.name.str.split("-", n=1).str[0].map(
    {"l2s": 0, "rlive": 1, "k": 2, "stable": 3})

rows = []
for _, row in d.sort_values(["max_check", "witness", "engine_order"],
                            ascending=[False, True, True], kind="stable").iterrows():
    path = Path(__file__).parent / "model" / f"{row['name'].split('-', 1)[1]}.aig"
    with path.open("rb") as f:
        header = f.readline().split()
        sizes = list(map(int, header[1:]))
        M, I, L, O, A, B, C, J, F = (sizes + [0] * 9)[:9]
        for _ in range((I if header[0] == b"aag" else 0) + L + O + B + C):
            f.readline()
        q = [int(f.readline()) + F for _ in range(J)]
    engine, name = row['name'].split('-', 1)
    engine = {"k": "k-liveness", "l2s": "L2S", "rlive": "rLive", "stable": "stabilizer"}[engine]
    rows.append([name, M, I, L, C, O + B,
                 *[q[i] if i < J else "-" for i in range(2)], engine,
                 row["Generation (s)"], row["Checking (s)"]])

heads = ["Model", "M", "I", "L", "C", "P (O+B)", "Q1", "Q2", "Engine",
         "Generate (s)", "Check (s)"]
previous = None
for row in rows:
    if row[0] == previous:
        row[:8] = [""] * 8
    else:
        previous = row[0]
table = pd.DataFrame(rows, columns=heads)
print(table.to_string(index=False, float_format=lambda v: f"{v:.2f}"))

time_widths = [max((f"{row[i]:.2f}" for row in rows), key=len, default="0.00") for i in (-2, -1)]

with open(f"{out}-checks.tex", "w") as f:
    f.write(r"\begin{table}[htbp]\centering" + "\n")
    f.write(r"\caption{Multi-signal liveness model sizes and \caketaiger witness runtimes, grouped by model and ordered by the highest checking time per model.}\label{tab:multi-checks}" + "\n")
    f.write(r"\begin{tabular*}{\linewidth}{@{}@{\extracolsep{\fill}}lrrrrrrr@{\extracolsep{0pt}\hspace{6pt}}|@{\hspace{6pt}}l@{\extracolsep{\fill}\hspace{4pt}}rr@{}}" + "\n")
    tex_heads = ["Model", "M", "I", "L", "C", "P", r"Q\textsubscript{1}", r"Q\textsubscript{2}", "Engine",
                 "Generate (s)", "Check (s)"]
    tex_heads[-2:] = [r"\multicolumn{1}{c}{" + h + "}" for h in tex_heads[-2:]]
    heading = r"\toprule" + "\n" + " & ".join(tex_heads) + r" \\ \midrule" + "\n"
    f.write(heading)
    previous = None
    for name, *cells in rows:
        if name and previous is not None and name != previous:
            f.write(r"\hline" + "\n")
        if name:
            previous = name
        cells = [f"{v:.2f}" if isinstance(v, float) else str(v) for v in cells]
        cells[-2:] = [r"\multicolumn{1}{c}{\phantom{" + w + r"}\llap{" + v + "}}"
                      for w, v in zip(time_widths, cells[-2:])]
        f.write(" & ".join([name.replace("_", r"\_"), *cells]) + r" \\" + "\n")
    f.write(r"\bottomrule\end{tabular*}\end{table}" + "\n")
