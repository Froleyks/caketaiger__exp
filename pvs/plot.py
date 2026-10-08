#!/usr/bin/env python3
"""PVS total runtimes and PAR-2 scores."""
from sys import argv
import pandas as pd

def cell(s):
    return r"{\small\texttt{\textgreater{}128GB}}" if s == "memout" else s

src, out, timeout = argv[1:]
timeout = float(timeout)
d = pd.read_csv(src)
d.loc[(d.dir == "pvs") & (d.status == "error-1"), "status"] = "memout"
cfgs = ["certifaiger", "caketaiger", "pvs"]
d["total"] = d.time.where(d.status == "ok")
times = d.pivot(index="name", columns="dir", values="total")[cfgs]
times = times.sort_values("pvs", ascending=False, na_position="first")
d["cell"] = d.time.map("{:.3f}".format).where(d.status == "ok", d.status)
t = d.pivot(index="name", columns="dir", values="cell").loc[times.index, cfgs]
scores = times.fillna(2 * timeout).mean()
rows = [[f"PAR-2 ({len(t)})", *(f"{v:.3f}" for v in scores)]]
rows += [[name, *row] for name, row in t.iterrows()]
widths = [max(col, key=len) for col in zip(*(row[1:] for row in rows))]

with open(f"{out}.tex", "w") as f:
    f.write(r"\noindent\begin{minipage}{\linewidth}\begin{center}" + "\n")
    f.write(r"\setlength{\tabcolsep}{8pt}" + "\n")
    f.write(r"\begin{tabular}{lrrr}\toprule" + "\n")
    heads = [r"\certifaiger (s)", r"\caketaiger (s)", r"\textsc{pvs} (s)"]
    f.write("Benchmark & " + " & ".join(r"\multicolumn{1}{c}{" + h + "}" for h in heads)
            + r" \\ \midrule" + "\n")
    for i, (name, *cells) in enumerate(rows):
        cells = [r"\multicolumn{1}{c}{\phantom{" + cell(w) + r"}\llap{" + cell(v) + "}}"
                 for w, v in zip(widths, cells)]
        f.write(" & ".join([name, *cells]) + r" \\" + (r" \midrule" if i == 0 else "") + "\n")
    f.write(r"\bottomrule\end{tabular}\end{center}" + "\n")
    f.write(r"\end{minipage}\par\vspace{1cm}" + "\n")
