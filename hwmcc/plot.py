#!/usr/bin/env python3
"""HWMCC summary, combined runtime CDF and Certifaiger/Caketaiger comparisons."""
from pathlib import Path
from math import exp, log
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
d.loc[d.status == "incomplete", "status"] = "timeout"
d["gen"] = d[["generation", "split", *d.filter(regex="^cnf_")]].sum(axis=1)
d["check"] = d.filter(regex="^check_").sum(axis=1)
d["ratio"] = d.filter(regex="^clauses_").sum(axis=1) / d.witness_M
# Scatter plots use the original statuses and all retained rows.
status = d.pivot(index="name", columns="dir", values="status")
plt.rcParams.update({"font.size": 16, "axes.labelsize": 16, "xtick.labelsize": 15,
                     "ytick.labelsize": 15, "legend.fontsize": 16})
for metric, title in [("gen", "Generation"), ("check", "Checking")]:
    times = d.pivot(index="name", columns="dir", values=metric)[["certifaiger", "caketaiger"]]
    if metric == "check":
        times = times.where(status == "ok")
    x, y = times.certifaiger, times.caketaiger
    lo, hi = times.min().min() / 1.2, times.max().max() * 1.2
    ratio = exp((y / x).dropna().map(log).mean())
    print(f"{title}: geometric mean Caketaiger/certifaiger-default ratio: {ratio:.2f}")
    start, end = max(lo, lo / ratio), min(hi, hi / ratio)
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot([lo, hi], [lo, hi], "--", color="gray", label="Equal time")
    ax.scatter(x, y, s=48, alpha=0.7)
    ax.plot([start, end], [ratio * start, ratio * end], color="tab:orange",
            label=f"geo. mean ({ratio:.2f})")
    if metric == "check":
        top = x[status.caketaiger == "timeout"].dropna()
        right = y[status.certifaiger == "timeout"].dropna()
        ax.scatter(top, [1.025] * len(top), transform=ax.get_xaxis_transform(),
                   clip_on=False, marker="x", color="tab:red", s=64,
                   label=rf"\caketaiger timeout ({(status.caketaiger == 'timeout').sum()})")
        ax.scatter([1.025] * len(right), right, transform=ax.get_yaxis_transform(),
                   clip_on=False, marker="+", color="tab:green", s=64,
                   label=rf"\certifaiger timeout ({(status.certifaiger == 'timeout').sum()})")
        both = ((status.caketaiger == "timeout") &
                (status.certifaiger == "timeout")).sum()
        if both:
            for marker, color in [("x", "tab:red"), ("+", "tab:green")]:
                ax.scatter([1.025], [1.025], transform=ax.transAxes,
                           clip_on=False, marker=marker, color=color, s=64)
    ax.set(xscale="log", yscale="log", xlim=(lo, hi), ylim=(lo, hi),
           xlabel=rf"\certifaiger {title.lower()} (s)", ylabel=rf"\caketaiger {title.lower()} (s)")
    ax.set_aspect("equal", adjustable="box")
    ax.grid(alpha=0.25)
    fig.legend(loc="upper center", bbox_to_anchor=(0.5, 0.17), ncol=2, frameon=False,
               handlelength=1.2, handletextpad=0.4, columnspacing=0.8)
    # Keep identical axes and page bounds despite the different legend heights.
    fig.subplots_adjust(left=0.19, bottom=0.30, right=0.91, top=0.96)
    fig.savefig(f"{out}-scatter-certifaiger-caketaiger-{metric}.pdf")
    plt.close(fig)

ok = d[d.status == "ok"]
plt.rcParams.update({"font.size": 15, "axes.labelsize": 16,
                     "xtick.labelsize": 15, "ytick.labelsize": 15,
                     "legend.fontsize": 15})
cfgs = ["caketaiger", "certifaiger", "certifaiger-coi+xor+ite",
        "certifaiger-coi+xor", "certifaiger-coi", "certifaiger-plain"]
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
# Use paired combined runtimes, rather than ratios of unpaired medians.
combined = common.assign(total=common.gen + common.check).pivot(
    index="name", columns="dir", values="total")
relative = combined.caketaiger / combined.certifaiger
median_ratio = relative.median()
geomean_ratio = exp(relative.map(log).mean())
print(f"Combined runtime reduction (intersection, per-certificate median / geometric mean): "
      f"{100 * (1 - median_ratio):.2f}% / {100 * (1 - geomean_ratio):.2f}%")

# Tables and CDF classify any SAT call above 3602 seconds as a timeout.
solved_10h = ok.groupby("dir").name.nunique()
d.loc[(d.filter(regex="^solve_") > 3602).any(axis=1), "status"] = "timeout"
ok = d[d.status == "ok"]
solved_1h = ok.groupby("dir").name.nunique()
print("HWMCC solved benchmarks (10-hour / 1-hour SAT-call time limit):")
for cfg in pair:
    print(f"  {cfg}: {solved_10h.get(cfg, 0)} / {solved_1h.get(cfg, 0)}")

# Mean clause/gate ratio, mean generation time, and checking PAR-2.
t = d.groupby("dir").agg(ratio=("ratio", "mean"), gen=("gen", "mean")).loc[cfgs]
t["timeout"] = (d.status == "timeout").groupby(d.dir).sum()
t["par2"] = d.check.where(d.status == "ok", 2 * timeout).groupby(d.dir).mean()
solved_all = d[(d.status == "ok") & d.dir.isin(cfgs)]
solved_counts = solved_all.groupby("name").dir.nunique()
common_names = solved_counts[solved_counts == len(cfgs)].index
print(f"HWMCC: {len(common_names)} benchmarks solved by all {len(cfgs)} configurations (Mean intersection)")
t["mean"] = solved_all[solved_all.name.isin(common_names)].groupby("dir").check.mean()
t = t[["ratio", "gen", "timeout", "mean", "par2"]]
table_labels = {c: label.replace(" ", r"\ {\fontsize{6}{7}\selectfont ", 1) + "}"
                if " " in label else label for c, label in labels.items()}
rows = [[table_labels[c], *(f"{v:.0f}" if i == 2 else f"{v:.2f}"
                       for i, v in enumerate(row))]
        for c, row in t.iterrows()]
widths = [max(col, key=len) for col in zip(*(row[1:] for row in rows))]
with open(f"{out}.tex", "w") as f:
    f.write(r"\begin{center}\begin{tabular}{@{}l@{}rr@{}p{4pt}@{}rrr@{}}\toprule" + "\n")
    f.write(r" & \multicolumn{2}{@{}c}{Generation} & & \multicolumn{3}{c@{}}{Checking} \\" + "\n")
    f.write(r"\cmidrule(lr){2-3}\cmidrule(lr){5-7}" + "\n")
    heads = ["Clause/gate", "Mean (s)", r"{\small\texttt{\textgreater{}1h}}", r"Mean$_{\cap}$(s)",
             "PAR-2 (s)"]
    heads = [r"\multicolumn{1}{c}{" + h + "}" for h in heads]
    heads[0] = heads[0].replace("{c}", "{@{}c}", 1)
    heads[-1] = heads[-1].replace("{c}", "{c@{}}", 1)
    heads.insert(2, "")
    f.write("Checker & " + " & ".join(heads)
            + r" \\ \midrule" + "\n")
    minima = t.min().to_numpy()
    for (name, *cells), values in zip(rows, t.to_numpy()):
        cells = [r"\multicolumn{1}{c}{\phantom{" + w + r"}\llap{"
                 + (r"{\bft " + v + "}" if value == minimum else v) + "}}"
                 for w, v, value, minimum in zip(widths, cells, values, minima)]
        cells[0] = cells[0].replace("{c}", "{@{}c}", 1)
        cells[-1] = cells[-1].replace("{c}", "{c@{}}", 1)
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

cdf_ok = ok.assign(combined=ok.gen + ok.check)
cdf_labels = {c: label.replace(r"\fontsize{6}{7}", r"\fontsize{10}{12}")
              for c, label in table_labels.items()}
lo, hi = cdf_ok.combined.min() / 1.2, cdf_ok.combined.max() * 1.2
fig, ax = plt.subplots(figsize=(9, 6))
for i, c in enumerate(cfgs):
    times = cdf_ok.loc[cdf_ok.dir == c, "combined"].sort_values()
    ax.step([lo, *times], range(len(times) + 1), where="post", linewidth=1.8,
            marker="o", markersize=2.5, alpha=0.8, markevery=range(1, len(times) + 1),
            zorder=2 + len(cfgs) - i, label=f"{len(times)} {cdf_labels[c]}")
ax.set(xscale="log", xlim=(lo, hi), ylim=(0, n * 1.02),
       xlabel="generation + checking (s)", ylabel="validated certificates")
ax.grid(alpha=0.25)
ax.legend(loc="lower right")
fig.tight_layout()
fig.savefig(f"{out}-cdf.pdf")
plt.close(fig)
