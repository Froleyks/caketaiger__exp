# Caketaiger experiments

Three separate benchmark sets compare **Certifaiger**, **Caketaiger**, and **PVS**.
This setup starts from the experiment template at commit `6f30029`.
No experimental runs or old measurements were imported. Build and execution
verification are still pending; no artifact badges or paper results are claimed.

## Experiments

| Experiment | Inputs | Checkers |
| --- | --- | --- |
| `multi` | Merged models and their published witnesses | Certifaiger, Caketaiger |
| `pvs` | The 13-model liveness comparison, currently a partial snapshot | Certifaiger and Caketaiger on Voiraig witnesses; PVS on nuXmv certificates |
| `hwmcc` | HWMCC'25 bit-level safety models and published UNSAT witnesses | Certifaiger, Caketaiger |

HWMCC also includes cumulative CNF configurations:

| Configuration | `aigtocnf` options |
| --- | --- |
| `certifaiger-plain` | `--no-coi --no-xor --no-ite --no-pg` |
| `certifaiger-coi` | `--no-xor --no-ite --no-pg` |
| `certifaiger-coi+xor` | `--no-ite --no-pg` |
| `certifaiger-coi+xor+ite` | `--no-pg` |

The existing `certifaiger` configuration is the final stage, with COI, XOR,
ITE and PG enabled (default options). The new configurations use the same generator, SAT solver and proof checker. Their
`our-data` rows copy the corresponding `certifaiger` runtimes
for packing and subset selection.
Run `make -C hwmcc benchmarks` to regenerate and pack the HWMCC
configuration lists without starting checks.

The three experiments have separate input sets, lists, logs, data and reports.
Matching basenames in `multi` and `pvs` do not identify the same model: the
multi models are merged inputs.

`multi/model/<name>.aig` and `multi/witness/<engine>-<name>.aig` were copied from
`/home/froleyks/Downloads/multi`. The initial copy contains 27 models and 81 witnesses.

`hwmcc/Makefile` downloads the safety models and log archive from
[HWMCC'25 on Zenodo](https://zenodo.org/records/17428464) and extracts models and
`certificate.unsat` files. These
archives have not been downloaded into this checkout yet.

Each `make_benchmarks.sh` uses `find` on its witness directory and derives the
model path from the witness name. There is no model/witness pairing manifest.
The HWMCC lists include every extracted `certificate.unsat`, without filtering
through the competition's results CSV.

## Preparation

Call make from the repository root. The top-level Makefile prepares shared tools
and the Python environment before calling the experiments; their Makefiles assume
these dependencies already exist.

```bash
make import          # refresh the multi/PVS copies from the local source paths
make check-setup     # syntax, local list generation, and input-path checks only
make download        # download and extract HWMCC inputs only
make setup           # build tools, Python environment, and download HWMCC inputs
make benchmarks      # generate all lists; downloads HWMCC inputs if missing
```

`make import` can be repeated when the local witness generation has progressed.
It copies existing files and does not start generation. Lists are regenerated
on the next benchmark or execution target.

Native preparation needs Bash, GNU make, Git, curl, tar, xz, GCC/G++, CMake,
SBCL, Python, uv, ripgrep and the usual C/C++ development libraries.
The Dockerfile records the container packages. The PVS source bundle includes
its Yices dependency; the Caketaiger and PVS source archives are included here.
Other source revisions are pinned in `src/Makefile`.

## Functional

**Execution commands below start runs when matching logs are missing.**
They were not run during setup on the resource-constrained local machine.

```bash
make smoketest                    # first two witnesses per checker, 10s per stage
make sub                          # reference-data subset, 1000s per stage
make all                          # complete lists, 3600s per stage
make all EXPERIMENTS=multi         # one experiment
make container-smoketest           # container execution; copies smoketest.pdf out
make container-sub
make container-all
```

Local/container execution runs the selected tasks, parses logs, and produces
`<goal>.pdf` next to the `<goal>/` plot directory. Existing `data-all`,
`data-sub` or `data-smoketest` files with no matching log directories are used
for reporting without preparing inputs or building checker tools. No reference measurements are included yet, so `sub`
currently uses the full available list with its shorter timeout. Once `our-data`
exists, `bin/pack.py` selects at most 28800 estimated seconds per experiment.
`make pilot` runs with a 10-second timeout and copies collected data to `our-data`.

For Mindwell, review `config.mk`, run `make setup`, then `make slurm`.
Slurm submission returns without waiting. Available logs are parsed and reports
attempted immediately; rerun `make all` after the jobs finish. The runner submits
missing logs on subsequent invocations. Each task atomically creates its log
before starting. Existing logs always skip that task, including interrupted or
failed tasks; delete the individual `.log` file to retry.

Reports show all recorded outcome categories and successful total runtimes.
No paper-specific claims or expected runtimes are stated before measurements
exist. The incomplete PVS snapshot must not be reported as a complete campaign.

## Collected data

HWMCC's `plot.py` removes the eight listed invalid benchmarks and changes
remaining `incomplete` statuses to `timeout`. PVS changes `error-1` to `memout`
for the PVS checker. Multi uses the data unchanged. The scripts then compute
the report's tables and plots without further data cleaning; input files stay
unchanged.

All three experiments append circuit statistics to `data-all`, `data-sub`, and
`data-smoketest` when collecting logs. Existing timing and status columns retain
their names and order. The additional columns are:

- `model_format`, `model_M`, `model_I`, `model_L`, `model_O`, `model_A`,
  `model_B`, `model_C`, `model_J`, `model_F`, and the corresponding `witness_`
  columns. The format is `aag` or `aig`; the numeric fields follow the AIGER
  header's MILOABCJF order. Omitted trailing counts are `NaN`.
- `shared`, from `Found symbol table mapping = for N literals`.
- `n_vars_<Check>` and `n_clauses_<Check>` for Reset, Transition, Safety,
  Liveness, Base, Inductive, Decrease, Closure, and Consistent, from the
  corresponding `n_vars_<Check>:` and `n_clauses_<Check>:` lines.

Unavailable measurements are `NaN`, including shared mappings not printed by
the checker and circuit statistics for PVS-only logs. Statistics are extracted
from existing logs. Existing saved CSVs cannot recover statistics that were
discarded; recollect their original logs to add them.
Reference `our-data` files remain separate from collected results.

The experiment Makefiles specify these fields through `bin/parse.py`'s generic
keyword/column/index interface. Indices count whitespace-separated words after
the matching text, starting at 1. For example, inspect the headers, shared
mapping, and Consistent counts in existing logs with:

```bash
bin/parse.py hwmcc/log-certifaiger-all @ time: @ status: \
  @ 'size model ' model_format 6 model_M 7 model_I 8 model_L 9 model_O 10 \
    model_A 11 model_B 12 model_C 13 model_J 14 model_F 15 \
  @ 'size witness ' witness_format 6 witness_M 7 witness_I 8 witness_L 9 \
    witness_O 10 witness_A 11 witness_B 12 witness_C 13 witness_J 14 witness_F 15 \
  @ 'Found symbol table mapping = for ' shared 1 \
  @ n_vars_Consistent: @ n_clauses_Consistent:
```

Collection reads each compact log once, searches its bytes directly, and emits
rows in directory/filename order. It requires Python 3.9 or later. The setup
uses `PARSE_JOBS` from `config.mk`; override it with `make ... PARSE_JOBS=2`.
The standalone parser defaults to one worker when `PARSE_JOBS` is unset and
also accepts `--jobs 2` to overlap reads. Pending work is bounded, so it
does not load a whole directory of logs into memory. Measure on the target
filesystem before increasing concurrency. Collection writes directly to the
data files.

Run the parser regression checks with
`python3 -m unittest discover -s tests -v`.

## Reusable

`config.mk` controls time, memory, CPUs and Slurm allocation. Limits apply to each
conversion, generation, SAT-solving and proof-checking stage separately.
The Slurm wall-time allowance is 4.1 times TIME.
`bin/certifaiger.sh` and `bin/caketaiger.sh` are adapted copies of Certifaiger's
`scripts/check_unsat.in` at revision `27d526e3e979074c3e92582768f577dc6eddb0da`.
They retain its parallel obligation checks and FIFO proof streaming, using
CaDiCaL and CakeLRUP. The Caketaiger copy consumes the CNFs emitted by Caketaiger.
Set `SEQUENTIAL=true` to use the upstream sequential option and increase SLACK
accordingly. PVS must produce a complete proof summary. Resource-limit,
checker-error and incomplete outcomes remain visible in collected results.

Workers place copied inputs, formulas, proofs and PVS contexts under
`SCRATCHDIR` (default: `VSC_SCRATCH`, then `TMPDIR`, then `/var/tmp`) and remove
their scratch directory on exit. Log directories retain compact output and
runlim measurements. `make clean` deletes logs, collected data and reports;
it preserves imported inputs, source archives and HWMCC downloads.

Container image preparation builds dependencies and fetches HWMCC inputs without
running experiments. Runtime containers use `--network none`. `make
caketaiger.tar.xz` and `make caketaiger.zip` package the committed Git `HEAD`,
so commit the completed setup and any intended saved data before packaging.
Container build, smoke execution, offline reporting and archive reload have not
yet been verified for this rebuilt setup.
