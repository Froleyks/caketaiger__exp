#!/usr/bin/env python3
"""HWMCC summary, checking CDF and Certifaiger/Caketaiger comparisons."""
from pathlib import Path
from sys import argv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

plt.rcParams.update({"font.size": 15, "axes.labelsize": 16, "axes.titlesize": 15,
                     "xtick.labelsize": 15, "ytick.labelsize": 15,
                     "legend.fontsize": 15, "legend.title_fontsize": 15,
                     "text.usetex": True,
                     "text.latex.preamble": r"\usepackage{xspace}"
                     r"\providecommand{\toolnameformat}[1]{\textsc{#1}\xspace}"
                     r"\providecommand{\caketaiger}{\toolnameformat{Caketaiger}}"
                     r"\providecommand{\certifaiger}{\toolnameformat{Certifaiger}}"})

labels = {
    "certifaiger": r"\certifaiger COI+XOR+ITE+PG",
    "certifaiger-plain": r"\certifaiger None",
    "certifaiger-coi": r"\certifaiger COI",
    "certifaiger-coi+xor": r"\certifaiger COI+XOR",
    "certifaiger-coi+xor+ite": r"\certifaiger COI+XOR+ITE",
    "caketaiger": r"\caketaiger",
}

src, out, timeout = argv[1:]
timeout = float(timeout)
d = pd.read_csv(src)
d = d[~d.name.isin(Path(__file__).with_name("invalid").read_text().split())].copy()
d["gen"] = d[["generation", "split", *d.filter(regex="^cnf_")]].sum(axis=1)
d["check"] = d.filter(regex="^check_").sum(axis=1)
d["ratio"] = d.filter(regex="^clauses_").sum(axis=1) / d.witness_M
ok = d[d.status == "ok"]
cfgs = ok.groupby("dir", sort=False).size().sort_values(ascending=False).index
n = d.name.nunique()

pair = ["caketaiger", "certifaiger"]
solved = ok[ok.dir.isin(pair)].groupby("name").size()
common = d[d.dir.isin(pair) & d.name.isin(solved[solved == 2].index)]
totals = common.groupby("dir")[["gen", "check"]].sum()
totals["total"] = totals.gen + totals.check
print(f"HWMCC: {n} retained benchmarks; {common.name.nunique()} solved by both (times in s)")
for cfg, label in zip(pair, ["Caketaiger", "certifaiger-default"]):
    r = d[d.dir == cfg]
    print(f"{label}: generation (all {len(r)}, total/mean/median): "
          f"{r.gen.sum():.2f}/{r.gen.mean():.2f}/{r.gen.median():.2f}")
    r = common[common.dir == cfg].copy()
    r["total"] = r.gen + r.check
    for statistic, heading in [("sum", "total"), ("mean", "mean"), ("median", "median")]:
        t = r[["gen", "check", "total"]].agg(statistic)
        print(f"  generation/checking/combined (intersection, {heading}): "
              f"{t.gen:.2f}/{t.check:.2f}/{t.total:.2f}")
pct = 100 * (totals.loc["caketaiger", "total"] / totals.loc["certifaiger", "total"] - 1)
print(f"Caketaiger is {abs(pct):.2f}% {'slower' if pct >= 0 else 'faster'} than certifaiger-default (combined, intersection)")

# Mean generation measurements and checking PAR-2.
t = d.groupby("dir")[["ratio", "gen"]].mean().loc[cfgs]
t["timeout"] = (d.status == "timeout").groupby(d.dir).sum()
t["par2"] = d.check.where(d.status == "ok", 2 * timeout).groupby(d.dir).mean()
rows = [[labels[c], *(f"{v:.2f}" if i in (1, 3) else
                       f"{v:.2f}".rstrip("0").rstrip(".")
                       for i, v in enumerate(row))]
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
    minima = t.min().to_numpy()
    for (name, *cells), values in zip(rows, t.to_numpy()):
        cells = [r"\multicolumn{1}{c}{\phantom{" + w + r"}\llap{"
                 + (r"{\bft " + v + "}" if value == minimum else v) + "}}"
                 for w, v, value, minimum in zip(widths, cells, values, minima)]
        cells.insert(2, "")
        f.write(" & ".join([name, *cells]) + r" \\" + "\n")
    f.write(r"\bottomrule\end{tabular}\end{center}" + "\n")

checks = [c.removeprefix("check_") for c in d.filter(regex="^check_")]
rows = [[c] for c in [*checks, "All", "Generation"]]
for cfg in ["caketaiger", "certifaiger"]:
    r = d[d.dir == cfg]
    vals = [((r[f"clauses_{c}"] / r.witness_M).mean(), r[f"check_{c}"].mean()) for c in checks]
    vals.append((r.ratio.mean(), r.check.mean()))
    for row, (ratio, time) in zip(rows, vals):
        row.extend([ratio, time])
    rows[-1].extend(["", r.gen.mean()])

maxima = [max(col) for col in zip(*(row[1:] for row in rows[:len(checks)]))]
fmt = lambda v, i: (f"{v:.2f}" if i % 2 else f"{v:.4f}") if v != "" else ""
widths = [max((fmt(v, i) for v in col), key=len)
          for i, col in enumerate(zip(*(row[1:] for row in rows)))]
with open(f"{out}-checks.tex", "w") as f:
    f.write(r"\begin{center}\begin{tabular}{lrr@{}p{8pt}@{}rr}\toprule" + "\n")
    f.write(r" & \multicolumn{2}{c}{\caketaiger} & & \multicolumn{2}{c}{\certifaiger} \\" + "\n")
    f.write(r"\cmidrule(lr){2-3}\cmidrule(lr){5-6}" + "\n")
    heads = ["Clause/gate", "Time (s)", "Clause/gate", "Time (s)"]
    heads = [r"\multicolumn{1}{c}{" + h + "}" for h in heads]
    heads.insert(2, "")
    f.write("Check & " + " & ".join(heads)
            + r" \\ \midrule" + "\n")
    for name, *cells in rows:
        if name in ("All", "Generation"):
            f.write(r"\midrule" + "\n")
        cells = [r"\multicolumn{1}{c}{\phantom{" + w + r"}\llap{"
                 + (r"{\bft " + fmt(v, i) + "}"
                    if name in checks and v == m else fmt(v, i)) + "}}"
                 for i, (w, v, m) in enumerate(zip(widths, cells, maxima))]
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
       xlabel="Time (s)", ylabel="Checked Certificates")
ax.grid(alpha=0.25)
ax.legend(loc="lower right")
fig.tight_layout()
fig.savefig(f"{out}-cdf.pdf")
plt.close(fig)

status = d.pivot(index="name", columns="dir", values="status")
plt.rcParams.update({"font.size": 16, "axes.labelsize": 16, "xtick.labelsize": 15,
                     "ytick.labelsize": 15, "legend.fontsize": 16})
for metric, title in [("gen", "Generation"), ("check", "Checking")]:
    times = d.pivot(index="name", columns="dir", values=metric)[["certifaiger", "caketaiger"]]
    if metric == "check":
        times = times.where(status == "ok")
    x, y = times.certifaiger, times.caketaiger
    lo, hi = times.min().min() / 1.2, times.max().max() * 1.2
    ratio = (y / x).median()
    print(f"{title}: median Caketaiger/certifaiger-default ratio: {ratio:.2f}")
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
                   label=rf"\caketaiger timeout ({len(top)})")
        ax.scatter([1.025] * len(right), right, transform=ax.get_yaxis_transform(),
                   clip_on=False, marker="x", color="tab:green", s=64,
                   label=rf"\certifaiger timeout ({len(right)})")
    ax.set(xscale="log", yscale="log", xlim=(lo, hi), ylim=(lo, hi),
           xlabel=rf"\certifaiger {title.lower()} (s)", ylabel=rf"\caketaiger {title.lower()} (s)")
    ax.set_aspect("equal", adjustable="box")
    ax.grid(alpha=0.25)
    fig.legend(loc="upper center", bbox_to_anchor=(0.5, 0.17), ncol=2, frameon=False,
               handlelength=1.2, handletextpad=0.4, columnspacing=0.8)
    fig.tight_layout(rect=(0, 0.16, 1, 1))
    fig.savefig(f"{out}-scatter-certifaiger-caketaiger-{metric}.pdf", bbox_inches="tight", pad_inches=0.3)
    plt.close(fig)
