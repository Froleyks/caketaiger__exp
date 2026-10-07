# Adapting the experiment template

Keep the setup small and include only dependencies used by the experiment.

Preserve these execution models:

- **Local/container:** one invocation of `make smoketest`, `make sub`, or
  `make all` runs the selected tasks to completion, parses their logs and produces
  a PDF containing all results for that goal, without further interaction.
  The `container-` targets also copy the PDF to the host. If the matching data
  file exists and there are no matching log directories, only plotting runs:
  use `PLOTTING` and skip input preparation and `RUNNING` dependencies.
- **Slurm:** when tasks need running, submit jobs and return without waiting.
  Continue parsing available logs and attempting plots/PDF generation in the
  same invocation. Missing or incomplete results may make plotting fail on the
  first invocation; this is expected. Rerun the goal to submit remaining tasks
  and refresh results, then run it again after jobs finish for the complete PDF.
- **Retries:** log-file existence is the sole skip condition. The user manually
  deletes individual `.log` files for aborted/failed tasks and reruns the goal.
  Log targets must invoke the runner on subsequent make invocations; existing
  log directories must not prevent that. The runner selects missing logs, and
  `run.sh` atomically creates each log before work starts to prevent duplicates.

To adapt:

- Complete the reviewer-facing `readme.md`: title, venue, experiments, paper
  figures/tables, runtimes and expected results. Keep its badge sections and
  document how reviewers can reproduce and assess the paper claims.
- Set `NAME` in `Makefile` and `config.mk`; set `EXPERIMENTS`, `PLOTTING`, and
  `RUNNING` in `Makefile`; copy/rename `experiment/`.
- Put pinned source builds in `src/Makefile`. Add only used packages to
  `Dockerfile`. Keep all setup, execution and reporting reachable via make.
- Set `CONFIGS` and declare the benchmark lists as grouped targets. Generate
  `command ... @group config name` lines; `config_name` must be unique. Commands
  must consume those final three fields rather than pass them to the tool.
- Adapt `bin/run.sh` for the concrete tool calls and configurations. Keep its
  atomic log creation before scratch setup or tool execution. An existing log
  always skips the task, including aborted/failed runs; the user deletes those
  logs manually to retry. Keep the `config_name.log` naming used by the runner.
- **Keep large files off the repository/home filesystem.** Inputs copied for a
  task, proofs, witnesses and intermediates belong in `$TMP` under `SCRATCHDIR`
  (defaults to `VSC_SCRATCH`, `TMPDIR`, or `/var/tmp`). Run tools from `$TMP` and
  redirect bulky tool output there. Keep `LOG` limited to compact logs and
  resource measurements.
- **Clean up scratch.** Preserve the exit/signal cleanup traps in `run.sh`,
  including on tool failure; pass `$TMP`/`TMPDIR` to tools creating temporary files.
- **Limit each stage separately:** `limit.sh generate ...`, `limit.sh check ...`,
  and individual calls for preprocessing/conversions. Adapt exit codes and stage
  dependencies to each tool; write total `time:` and experiment-specific `status:`.
  Preserve timeout, memory, unknown and checker failures. Exit zero alone does
  not prove success.
- Match parser keywords and `plot.py` to those logs. Preserve `dir,name,time`
  in each experiment's `our-data` reference measurements. Always pass `our-data`
  to `pack.py` for packing and subset selection. Keep these separate from collected
  `data` files; missing `our-data` leaves lists unchanged. Choose meaningful
  smoke cases and `SUBSET` filters.
- `make pilot` runs `all` with `TIME=10` and copies each experiment's `data-all`
  to `our-data`. Existing logs retain their usual skip behaviour; on Slurm,
  rerun after the jobs finish to collect and copy the complete results.
- Keep `data-all` for `all`, `data-sub` for `sub`, and `data-smoketest` for
  `smoketest`, with the corresponding log directories for each goal.
- Tune `TIME`, `CPUS`, `MEM_PER_CPU`, `SLACK` for the concrete tool. Mindwell uses
  `batch_graniterapids`; account defaults to `lp_certifox`. Prefer static tools
  and check runtime compatibility on compute nodes.
- Complete image preparation before offline execution (`--network none`).
  Exercise smoke execution, cached-data plotting and archive reload with the
  chosen engine. The archive target packages committed Git HEAD.
- Change cluster source locally through Git; never patch remote files directly.
  Submit only when requested; after jobs finish run make to collect and plot.
  Inspect experiment/checker logs, not only Slurm completion.

Use one goal per make invocation. `make clean` removes logs and the container;
preserve results first. Do not claim a runnable experiment until the hooks are
adapted and its actual smoke run and report have been checked.
