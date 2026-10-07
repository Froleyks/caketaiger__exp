#!/usr/bin/env python3
"""Multi-property benchmark summary and per-check means."""
from pathlib import Path
from statistics import mean
from sys import argv
import pandas as pd

src, out = argv[1:]
d = pd.read_csv(src)
d["gen"] = d[["generation", "split", *d.filter(regex="^cnf_")]].sum(axis=1)
d["check"] = d.filter(regex="^check_").sum(axis=1)
d["ratio"] = d.filter(regex="^clauses_").sum(axis=1) / d.witness_M

if (Path(__file__).parent / "model").is_dir():
    props = []
    for name in d.name.unique():
        path = Path(__file__).parent / "model" / f"{name.split('-', 1)[1]}.aig"
        with path.open("rb") as f:
            M, I, L, O, A, B, C, J, *F = map(int, f.readline().split()[1:])
            for _ in range(L + O + B + C):
                f.readline()
            q = [int(f.readline()) + sum(F) for _ in range(J)]
        props.append((O + B, J, C, q))
    p, j, c, q = zip(*props)
    max_signals = [max(signals) for signals in q if signals]
    print(f"The {len(props)} benchmarks have")
    print(f"between {min(p)} and {max(p)} safety properties (mean {mean(p):.2f}),")
    print(f"between {min(j)} and {max(j)} liveness properties (mean {mean(j):.2f})")
    print(f"with between {min(max_signals)} and {max(max_signals)} signals (mean {mean(max_signals):.2f}),")
    print(f"and between {min(c)} and {max(c)} constraints (mean {mean(c):.2f}).")

checks = [c.removeprefix("check_") for c in d.filter(regex="^check_")]
rows = [[c] for c in [*checks, "All", "Generation"]]
for cfg in ["caketaiger", "certifaiger"]:
    r = d[d.dir == cfg]
    vals = [((r[f"clauses_{c}"] / r.witness_M).mean(), r[f"check_{c}"].mean()) for c in checks]
    vals.append((r.ratio.mean(), r.check.mean()))
    for row, (ratio, time) in zip(rows, vals):
        row.extend([f"{ratio:.4f}", f"{time:.4f}"])
    rows[-1].extend(["", f"{r.gen.mean():.4f}"])

widths = [max(col, key=len) for col in zip(*(row[1:] for row in rows))]
with open(f"{out}-checks.tex", "w") as f:
    f.write(r"\begin{center}\resizebox{.98\linewidth}{!}{\begin{tabular}{lrrrr}\toprule" + "\n")
    f.write(r" & \multicolumn{2}{c}{Caketaiger} & \multicolumn{2}{c}{Certifaiger} \\" + "\n")
    f.write(r"\cmidrule(lr){2-3}\cmidrule(lr){4-5}" + "\n")
    heads = ["Clause/gate", "Time (s)", "Clause/gate", "Time (s)"]
    f.write("Check & " + " & ".join(r"\multicolumn{1}{c}{" + h + "}" for h in heads)
            + r" \\ \midrule" + "\n")
    for name, *cells in rows:
        if name in ("All", "Generation"):
            f.write(r"\midrule" + "\n")
        cells = [r"\multicolumn{1}{c}{\phantom{" + w + r"}\llap{" + v + "}}"
                 for w, v in zip(widths, cells)]
        f.write(" & ".join([name, *cells]) + r" \\" + "\n")
    f.write(r"\bottomrule\end{tabular}}\end{center}" + "\n")
    f.write(r"Per-benchmark means. Clause/gate is $\mathrm{clauses}_{\mathrm{check}} / "
            r"M_{\mathrm{witness}}$. All sums the individual checks. "
            "Generation sums generator, split and CNF-conversion times; these stages may overlap.\n")
