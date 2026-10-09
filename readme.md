# Caketaiger experiments

This artifact produces the seven plots and tables used in the paper from three
experiments. Saved measurements are included; `make` rebuilds the report without
running certificate checkers when the corresponding log directories are absent.

## Experiments

| Experiment | Certificates | Checkers | Paper outputs |
| --- | ---: | --- | --- |
| `multi` | 81 | Caketaiger | Model sizes and generation/checking times, grouped by model; groups with a runtime above 5 seconds |
| `pvs` | 11 pairs | Caketaiger on Voiraig witnesses; PVS on nuXmv certificates | Model sizes, witness shoals and total runtimes |
| `hwmcc` | 984 per configuration | Caketaiger and five Certifaiger configurations | Summary and per-obligation tables, checking CDF, generation and checking scatter plots |

The HWMCC Certifaiger configurations enable no optimizations, COI, COI+XOR,
COI+XOR+ITE, and COI+XOR+ITE+PG (the default). All six checker configurations
are needed by the paper. The eight known invalid certificates in `hwmcc/invalid`
are excluded when generating task lists and plotting historical logs.
Certifaiger is not run on Multi or PVS. PVS task lists retain only models with
both kinds of certificate, including paired smoke and subset selections.

The paper outputs are:

- `hwmcc-all.tex` and `hwmcc-all-checks.tex`
- `hwmcc-all-cdf.pdf`
- `hwmcc-all-scatter-certifaiger-caketaiger-gen.pdf`
- `hwmcc-all-scatter-certifaiger-caketaiger-check.pdf`
- `multi-all-checks.tex`
- `pvs-all.tex`

`sub` and `smoketest` use the same output types with the corresponding suffix.
Each report directory copies PDF and TeX outputs prefixed with the experiment
name and selected effort; `all.pdf`, `sub.pdf`, and `smoketest.pdf` collect those outputs.

## Preparation

Run make from the repository root. Python dependencies are installed into
`.venv` using uv. Native execution additionally needs Bash, GNU make, Git, curl,
tar, xz, GCC/G++, CMake, SBCL, ripgrep and the libraries in `Dockerfile`.
Source revisions and bundled source builds are defined in `src/Makefile`.
PDF generation needs pdflatex or the bundled Tectonic executable. Matplotlib's
TeX labels additionally need a working LaTeX installation.

Multi and PVS inputs are in `benchmarks.tar.xz`. A saved-data Multi report only
extracts `multi/model`, to read its AIGER property counts. Checker builds and
witness preparation are skipped for cached reports. HWMCC execution downloads
models and certificates from [HWMCC'25 on Zenodo](https://zenodo.org/records/17428464).
When execution needs tools, the shared dependencies are built with one
`make -C src all` call.

```bash
make                              # regenerate all paper outputs and all.pdf
make all EXPERIMENTS=multi         # one experiment
make -C multi benchmarks          # generate lists from extracted inputs
make -C pvs benchmarks
make -C hwmcc benchmarks           # downloads HWMCC inputs if absent
```

## Functional

**These goals start runs when saved data are absent or matching log directories
exist.** Existing `.log` files are the sole skip condition. To retry a failed or
interrupted task, delete its individual `.log` file and rerun the goal.

```bash
make smoketest                    # two certificates per checker, 10s per stage
make sub                          # at most 28800 reference seconds per experiment
make all                          # full retained lists, 3600s per stage
make slurm                        # prepare inputs/tools and submit missing tasks
make container-smoketest          # container run; copies smoketest.pdf to host
make container-sub
make container-all
```

Local execution completes the tasks before parsing and plotting. Slurm returns
after submission and attempts a partial report; rerun the goal after jobs finish.
`config.mk` controls stage time/memory limits and Slurm resources. Workers put
inputs and intermediate files under `SCRATCHDIR` and clean up on exit. Logs and
resource measurements remain in each experiment's `log-<checker>-<goal>` directory.
The certificate runners retain their SAT solving, LRAT proof verification and
PVS proof-summary checks.

## Collected data

All three experiments parse the full set of columns: time, status, memory,
generation and splitting times, per-obligation CNF/solving/checking times,
model and witness AIGER headers, and per-obligation variable and clause counts.
The parser also records `dir` and `name` for task identity.

The saved HWMCC results exclude invalid certificates and classify the seven
previously incomplete runs as timeouts. The two known PVS memory-outs are stored
as `memout`. Newly collected errors remain as recorded by the runners.
The plotting scripts preserve the paper's timing definitions: checking is the
sum of obligation times; Certifaiger generation includes splitting and CNF
conversion; PVS comparison uses recorded total wall time.

Each experiment's `our-data` is a complete copy of `data-all`, used for task
packing and subset selection. `make pilot` runs with a 10-second limit and
copies the complete collected data to `our-data`. The parser extracts only the
fields declared in each experiment's Makefile.

## Reusable

`make clean` removes logs, generated reports, collected data and extracted inputs.
Preserve results before using it. Container execution uses `--network none` after
image preparation; building the image runs the smoke goal. The container and
archive entrypoints are retained but have not been revalidated by this cleanup.
`make caketaiger.tar.xz` and `make caketaiger.zip` package committed Git HEAD.
