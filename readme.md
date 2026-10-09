# Caketaiger: A Verified Certificate Checker for Hardware Model Checking

Evaluation on witness circuits for model checking safety and liveness properties.

Claimed badges: Available + Functional + Reusable

## Quickstart

```bash
make container-smoketest
make container-sub
make container-all
```

This extracts and loads the container image and runs different subsets of the experiments within the container.
If neither an image nor `caketaiger.tar.xz` is available, the image is built from the current directory instead.
PDFs with the results are copied to the current directory for inspection.
You may need to adjust the memory available per CPU used for each benchmark at the top of the Makefile before running `sub`.
(The Makefile is copied into the running container.)
`<system CPUs> * $(MEM_PER_CPU) * $(MAKEFLAGS --jobs)` should not exceed your system's memory (by much).
The `all` goal exercises the plotting scripts using our data without rerunning experiments in the prepared image.

`smoketest.pdf` should contain four tables and three plots. The smoke goal runs two certificates per checker with a 10-second limit per stage.
`all.pdf` should reproduce the plots and tables in the paper, without the surrounding paper text.
`sub.pdf` should approximate `all.pdf` while using lower timeouts, memory limits, and fewer benchmarks.

## Requirements

- `make`, `xz`, and either `podman` or `docker`
- Sufficiently large overlay storage for the container

## Experiments

Our evaluation consists of three experiments:

- `hwmcc`: comparison of Caketaiger to Certifaiger on HWMCC'25 safety certificates, including AIGER to CNF feature impact
- `pvs`: comparison of Caketaiger on Voiraig witnesses to the PVS-based checker on nuXmv certificates
- `multi`: certification of multi-signal and multi-property benchmarks

HWMCC checks 984 certificates with each of six configurations: Caketaiger, and Certifaiger with no optimizations, COI, COI+XOR, COI+XOR+ITE, and COI+XOR+ITE+PG (the default).
The eight known invalid HWMCC certificates listed in `hwmcc/invalid` are excluded.
PVS compares certificates for 11 models for which both nuXmv and Voiraig produced certificates.
Multi checks 81 witness circuits with Caketaiger.

## Functional

The artifact aims to provide evidence for our results while being as user-friendly as possible.
This includes minimal interaction, parallel execution, and benchmark selection.
You can `make enter` or `make extract` to inspect the setup in the running container or extract all files to the current directory.
`make stop` halts the containerized execution. Be aware that `make clean` will delete the running container.

The results produced by `sub` are intended to support the claims in the paper while being reasonably reproducible on a single machine.
You can modify the `SUBSET` parameter at the top of the Makefile to influence what benchmarks are rerun.
By default, the subset budget is 28800 (1/3 * 8h) per experiment..
This is a selection budget based on our measurements, rather than a wall-time limit for the entire experiment.
The `sub` goal also reduces the per-stage timeout from 3600 to 1000 seconds and the memory per allocated CPU from 4000 to 1400 MB.
Removing the `SUBSET` restriction and the two `sub` resource overrides will reproduce our results more precisely and increase the artifact runtime and memory requirements.
Changing `SUBSET` and rerunning will extend the results without redoing previous work where logs already exist.

With the default settings, `sub` is intended to show the following:
The Multi table demonstrates checking of models with multiple safety and liveness properties, using witnesses from different Voiraig engines.
The PVS table should reflect that Caketaiger is faster on average on the commonly certified benchmarks.
The two PVS memory-outs in the full results need not be reproduced with the reduced memory limit; additional memory-outs may occur.
The HWMCC checking-time plot and summary should show the benefit of the CNF optimizations and the competitive checking performance of Caketaiger.
The scatter plots distinguish formula generation, where Caketaiger is slower, from checking, where it performs better overall.
Exact runtimes, timeout counts, and relative ordering may vary with the machine and selected subset.

We recognize that the selection of the benchmark subset could influence the results.
While the script to select the subsets is available, it relies on our experimental data.
To fully reproduce all results, significant compute resources are necessary.
The setup to run on a Slurm cluster is included. To use it:

- `make extract`
- `make .venv` (uses uv)
- install dependencies (see Dockerfile)
  + most standalone tools are linked statically to ease execution on another machine
  + SBCL is required for the PVS-based checker
- adjust `config.mk` to your target cluster
- `make slurm` deletes cached `data-all` files and submits missing experiments
- run `make` once all jobs have finished to produce the final results
This will work the same without Slurm; however, it is unrealistic to run on a single machine.

## Reusable

The source code and toolchains used in the experiments are included in `src` and can be built with `src/Makefile`.
The experiment-specific orchestration lives in the `multi/`, `pvs/`, and `hwmcc/` Makefiles.
The Makefiles are extensive and document as much of the setup as possible.
This includes the fetching of source code, binaries, and benchmarks.
Multi and PVS inputs are included in `benchmarks.tar.xz`; HWMCC inputs are fetched from the HWMCC'25 archives when needed.

The three experiments run their checker configurations as follows:

- the top-level `Makefile` calls make in each subdirectory (multi, pvs, hwmcc) with the current goal (smoketest, sub, all)
- for each configuration and goal, a `benchmarks-` list is produced
- each line runs `bin/run.sh`, which invokes the corresponding `bin/caketaiger.sh`, `bin/certifaiger.sh`, or `bin/pvs.sh` script to check an existing certificate
- `bin/pack.py` optimizes the `benchmarks-` lists for parallel execution and subset selection using each experiment's `our-data`
- `bin/parallel.sh` uses Slurm if available and otherwise falls back to GNU parallel or xargs to produce `log-` directories
- `bin/parse.py` processes the logs and produces `data-<goal>` files with times, statuses, memory use, model/witness sizes, and per-obligation measurements
- each experiment's `plot.py` reads the data and produces the plots and tables used in the paper
- `bin/tex.sh` renders the experimental results using LaTeX

For convenience, targets with the `container-` prefix extract, load, and run the image, then forward the make call to the persistent container.
If a PDF is produced, it is copied to the current directory.

The experimental setup is intended to be easily reused for this or other experiments running locally or on HPC.
For usage of our tools, see the respective GitHub pages:

- [Caketaiger](https://github.com/CakeML/cakeml/tree/hwmcc)
- [Certifaiger](https://github.com/Froleyks/certifaiger)
- [Voiraig](https://github.com/Froleyks/voiraig)

Nils Froleyks
KU Leuven
2026-10-09
