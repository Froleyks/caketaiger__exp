#!/usr/bin/env python3
"""HWMCC summary, checking CDF and Certifaiger/Caketaiger comparisons."""
from sys import argv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

plt.rcParams.update({"font.size": 14, "axes.labelsize": 14, "axes.titlesize": 14,
                     "xtick.labelsize": 14, "ytick.labelsize": 14,
                     "legend.fontsize": 14, "legend.title_fontsize": 14})

invalid = '''
aic3_bitlevel_safety_2019_wolf_2019C_qspiflash_dualflexpress_divthree-p120.aig
aic3_bitlevel_safety_2020_mann_stack-p0.aig
avy_bitlevel_safety_2025_hkust_benchmarks_output_btor2_example_301_miter_miter.aig
ric3-multi_bitlevel_safety_2024_sosylab_floats-esbmc-regression_Float_div.i.p+cfa-reducer.aig
ric3-multi_bitlevel_safety_2024_sosylab_loops-crafted-1_sumt3.aig
ric3-multi_bitlevel_safety_2025_hkust_benchmarks_output_btor2_example_263_miter_miter.aig
ric3-multi_bitlevel_safety_2025_hkust_benchmarks_output_btor2_example_499_miter_miter.aig
avy_bitlevel_safety_2024_sosylab_product-lines_elevator_spec3_product18.cil.aig
'''.split()
labels = {
    "certifaiger": "Certifaiger COI+XOR+ITE+PG",
    "certifaiger-plain": "Certifaiger None",
    "certifaiger-coi": "Certifaiger COI",
    "certifaiger-coi+xor": "Certifaiger COI+XOR",
    "certifaiger-coi+xor+ite": "Certifaiger COI+XOR+ITE",
    "caketaiger": "Caketaiger",
}

src, out, timeout = argv[1:]
timeout = float(timeout)
d = pd.read_csv(src)
d = d[~d.name.isin(invalid)].copy()
d.loc[d.status == "incomplete", "status"] = "timeout"
d["gen"] = d[["generation", "split", *d.filter(regex="^cnf_")]].sum(axis=1)
d["check"] = d.filter(regex="^check_").sum(axis=1)
d["ratio"] = d.filter(regex="^clauses_").sum(axis=1) / d.witness_M
ok = d[d.status == "ok"]
cfgs = ok.groupby("dir", sort=False).size().sort_values(ascending=False).index
n = d.name.nunique()

# Mean generation measurements and checking PAR-2.
t = d.groupby("dir")[["ratio", "gen"]].mean().loc[cfgs]
t["timeout"] = (d.status == "timeout").groupby(d.dir).sum()
t["par2"] = d.check.where(d.status == "ok", 2 * timeout).groupby(d.dir).mean()
table_labels = {c: r"\textsc{" + tool + "}" + (" " + opt if opt else "")
                for c, label in labels.items() for tool, _, opt in [label.partition(" ")]}
rows = [[table_labels[c], *(f"{v:.2f}".rstrip("0").rstrip(".") for v in row)]
        for c, row in t.iterrows()]
widths = [max(col, key=len) for col in zip(*(row[1:] for row in rows))]
with open(f"{out}.tex", "w") as f:
    f.write(r"\begin{center}\begin{tabular}{lrr@{}p{8pt}@{}rr}\toprule" + "\n")
    f.write(r" & \multicolumn{2}{c}{Generation} & & \multicolumn{2}{c}{Checking} \\" + "\n")
    f.write(r"\cmidrule(lr){2-3}\cmidrule(lr){5-6}" + "\n")
    heads = ["Clause/gate", "Time (s)", "Timeout", "PAR-2 (s)"]
    heads = [r"\multicolumn{1}{c}{" + h + "}" for h in heads]
    heads.insert(2, "")
    f.write("Checker & " + " & ".join(heads)
            + r" \\ \midrule" + "\n")
    for name, *cells in rows:
        cells = [r"\multicolumn{1}{c}{\phantom{" + w + r"}\llap{" + v + "}}"
                 for w, v in zip(widths, cells)]
        cells.insert(2, "")
        f.write(" & ".join([name, *cells]) + r" \\" + "\n")
    f.write(r"\bottomrule\end{tabular}\end{center}" + "\n")

lo, hi = ok.check.min() / 1.2, ok.check.max() * 1.2
fig, ax = plt.subplots(figsize=(9, 6))
for i, c in enumerate(cfgs):
    times = ok.loc[ok.dir == c, "check"].sort_values()
    ax.step([lo, *times], range(len(times) + 1), where="post", linewidth=1.8,
            marker="o", markersize=2.5, alpha=0.8, markevery=range(1, len(times) + 1),
            zorder=2 + len(cfgs) - i, label=f"{len(times)} {labels[c]}")
ax.set(xscale="log", xlim=(lo, hi), ylim=(0, n * 1.02),
       xlabel="Check time (s)", ylabel="Cumulative benchmarks solved")
ax.grid(alpha=0.25)
ax.legend(loc="lower right")
fig.tight_layout()
fig.savefig(f"{out}-cdf.pdf")
plt.close(fig)

status = d.pivot(index="name", columns="dir", values="status")
plt.rcParams.update({"font.size": 16, "axes.labelsize": 16, "xtick.labelsize": 14,
                     "ytick.labelsize": 14, "legend.fontsize": 16})
for metric, title in [("gen", "Generation"), ("check", "Checking")]:
    times = d.pivot(index="name", columns="dir", values=metric)[["certifaiger", "caketaiger"]]
    if metric == "check":
        times = times.where(status == "ok")
    x, y = times.certifaiger, times.caketaiger
    lo, hi = times.min().min() / 1.2, times.max().max() * 1.2
    ratio = (y / x).median()
    start, end = max(lo, lo / ratio), min(hi, hi / ratio)
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot([lo, hi], [lo, hi], "--", color="gray", label="Equal time")
    ax.scatter(x, y, s=48, alpha=0.7)
    ax.plot([start, end], [ratio * start, ratio * end], color="tab:orange",
            label=f"median ({ratio:.2f})")
    if metric == "check":
        top = x[status.caketaiger == "timeout"].dropna()
        right = y[status.certifaiger == "timeout"].dropna()
        ax.scatter(top, [1.025] * len(top), transform=ax.get_xaxis_transform(),
                   clip_on=False, marker="x", color="tab:red", s=64,
                   label=f"Caketaiger timeout ({len(top)})")
        ax.scatter([1.025] * len(right), right, transform=ax.get_yaxis_transform(),
                   clip_on=False, marker="x", color="tab:green", s=64,
                   label=f"Certifaiger timeout ({len(right)})")
    ax.set(xscale="log", yscale="log", xlim=(lo, hi), ylim=(lo, hi),
           xlabel=f"Certifaiger {title.lower()} (s)", ylabel=f"Caketaiger {title.lower()} (s)")
    ax.set_aspect("equal", adjustable="box")
    ax.grid(alpha=0.25)
    fig.legend(loc="upper center", bbox_to_anchor=(0.5, 0.17), ncol=2, frameon=False,
               handlelength=1.2, handletextpad=0.4, columnspacing=0.8)
    fig.tight_layout(rect=(0, 0.16, 1, 1))
    fig.savefig(f"{out}-scatter-certifaiger-caketaiger-{metric}.pdf")
    plt.close(fig)
