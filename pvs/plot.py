#!/usr/bin/env python3
"""PVS total runtimes and CakeTiger comparison."""
from sys import argv
import pandas as pd

def cell(s):
    return r"{\small\texttt{\textgreater{}128GB}}" if s == "memout" else s

src, out = argv[1:]
d = pd.read_csv(src)
cfgs = ["caketaiger", "pvs"]
d["total"] = d.time.where(d.status == "ok")
times = d.pivot(index="name", columns="dir", values="total")[cfgs]
times = times.sort_values("pvs", ascending=False, na_position="first")
d["cell"] = d.time.map("{:.2f}".format).where(d.status == "ok", d.status)
t = d.pivot(index="name", columns="dir", values="cell").loc[times.index, cfgs]
witness = d[d.dir == "caketaiger"].set_index("name")
fields = ["model_M", "model_I", "model_L", "witness_C"]
paired = times.dropna()
rows = [[name, *(f"{int(witness.loc[name, field])}" for field in fields), *row]
        for name, row in t.iterrows()]
rows.append([f"Mean ({len(paired)})", *([""] * len(fields)),
             *(f"{v:.2f}" for v in paired.mean())])
memouts = t.eq("memout").any(axis=1).sum()
widths = [max(col, key=len) for col in zip(*(row[1:] for row in rows))]

with open(f"{out}.tex", "w") as f:
    f.write(r"\noindent\begin{minipage}{\linewidth}\begin{center}" + "\n")
    f.write(r"\setlength{\tabcolsep}{4pt}" + "\n")
    f.write(r"\begin{tabular}{lrrrrrr}\toprule" + "\n")
    f.write(r" & \multicolumn{3}{c}{Model} & Witness & \multicolumn{2}{c}{Total time (s)} \\" + "\n")
    f.write(r"\cmidrule(lr){2-4}\cmidrule(lr){5-5}\cmidrule(lr){6-7}" + "\n")
    heads = ["M", "I", "L", "shoals", r"\caketaiger", r"\textsc{pvs}"]
    f.write(" & " + " & ".join(r"\multicolumn{1}{c}{" + h + "}" for h in heads)
            + r" \\ \midrule[\heavyrulewidth]" + "\n")
    for i, (name, *cells) in enumerate(rows):
        runtimes = times.loc[name] if name in times.index else paired.mean()
        cells[-2:] = [r"{\bft " + v + "}" if runtime == runtimes.min() else v
                      for v, runtime in zip(cells[-2:], runtimes)]
        cells = [r"\multicolumn{1}{c}{\phantom{" + cell(w) + r"}\llap{" + cell(v) + "}}"
                 if j >= len(fields) else v
                 for j, (w, v) in enumerate(zip(widths, cells))]
        f.write(" & ".join([name, *cells]) + r" \\" + (r" \midrule[\heavyrulewidth]" if i == memouts - 1
                                     else r" \midrule" if i == len(rows) - 2 else "") + "\n")
    f.write(r"\bottomrule\end{tabular}\end{center}" + "\n")
    f.write(r"\end{minipage}\par\vspace{1cm}" + "\n")
