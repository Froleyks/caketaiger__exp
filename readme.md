# Caketaiger: A Verified Certificate Checker for Hardware Model Checking

Claimed badges: Available + Functional + Reusable

## Quickstart

```bash
make container-smoketest
make container-all
make container-sub
```

This extracts and loads the correct (amd/arm) container image and runs different subsets of the experiments within the container.
PDFs with the results are copied to the current directory for inspection.
Wall times measured on the two platforms we tested:

| Step                       | MacBook (arm) | EC2 (amd) |
|----------------------------|---------------|-----------|
| `unzip`                    | 6s            | 11s       |
| `make container-smoketest` | 50s           | 1m34s     |
| `make container-all`       | 1s            | 3s        |
| `make container-sub`       | 3h22m58s      | 6h03m32s  |

- MacBook: Apple M5 Max, 18 cores, 64 GB, macOS 26.5.1, Docker Desktop (Docker 29.8.2), ARM image
- EC2: m7i.4xlarge, 16 vCPUs (Intel), 64 GiB, Ubuntu 24.04 LTS, podman, AMD image

Windows+Mac: Adjust the Docker Desktop memory limit to all you have and adjust the values at the top of the Makefile accordingly.
(The Makefile is copied into the running container.)
`<system CPUs> * $(MEM_PER_CPU) * $(MAKEFLAGS --jobs)` should not exceed your system's memory (by much).
The `all` goal exercises the plotting scripts using our data without rerunning experiments in the prepared image.

`smoketest.pdf` should contain three tables and three plots. The smoke goal runs two certificates per checker with a 10-second limit per stage.
`all.pdf` should exactly reproduce the plots and tables in the paper (except for fonts).
`sub.pdf` should approximate `all.pdf` while using lower timeouts, memory limits, and fewer benchmarks.

## Requirements

- `make`, `xz`, and either `podman` or `docker`
- About 32 GB of memory available to the container
- About 16 GB of free disk space (archive, extracted images, loaded image, and container)

## Experiments

Our evaluation consists of three experiments:

- `hwmcc`: comparison of Caketaiger to Certifaiger on HWMCC'25 safety certificates, including AIGER to CNF feature impact
- `pvs`: comparison of Caketaiger on Voiraig witnesses to the PVS-based checker on nuXmv certificates
- `multi`: certification of multi-signal and multi-property benchmarks

HWMCC checks 983 certificates with each of six configurations: Caketaiger, and Certifaiger with no optimizations, COI, COI+XOR, COI+XOR+ITE, and COI+XOR+ITE+PG (the default).
The nine known invalid HWMCC certificates listed in `hwmcc/invalid` are excluded.
PVS compares certificates for 11 models for which both nuXmv and Voiraig produced certificates.
Multi checks 81 witness circuits with Caketaiger.

## Functional

The artifact aims to provide evidence for our results while being as user-friendly as possible.
This includes minimal interaction, parallel execution, and benchmark selection.
You can `make enter` or `make extract` to inspect the setup in the running container or extract all files to the current directory.
`make stop` halts the containerized execution. Be aware that `make clean` will delete the running container.

The results produced by `sub` are intended to support the claims in the paper while being reasonably reproducible on a single machine.
You can modify the `SUBSET` parameter at the top of the Makefile to influence what benchmarks are rerun.
By default, the subset budget is 28800 (1/3 * 8h) per experiment.
This is a selection budget based on our measurements, rather than a wall-time limit for the entire experiment.
The `sub` goal also reduces the per-stage timeout from 10 hours to 1 hour.
To approximate the results we got using 2 core-years on our cluster, HWMCC `sub` runs in two parts.
The parallel part checks the 681 certificates all configurations validate within 1500 MB in our data.
The sequential part checks 22 additional certificates needing up to 26 GB one at a time, selected by `hwmcc/sequential.py`.
Multi `sub` reruns 19 witnesses, as many as the paper's Multi table shows: those of 6s217 and cuabq2f from that table, and of the next hardest models cuffl, culock, cutarb8, and cugcd. As the table has been moved to the appendix, we replaced the most expensive witnesses with cheaper ones.
The PVS experiment runs in full.
Removing the `SUBSET` restriction and the two `sub` resource overrides will reproduce our results more precisely and increase the artifact runtime and memory requirements.
Changing `SUBSET` and rerunning will extend the results without redoing previous work where logs already exist.

With the default settings, `sub` is intended to show the following:
The Multi table demonstrates that checking models with multiple safety and liveness properties is possible.
The PVS table should reflect that Caketaiger is considerably faster.
The two PVS memory-outs in the full results need not be reproduced and may be timeouts instead.
The HWMCC table should show that Caketaiger produces the fewest clauses per gate and has the lowest mean checking time on the commonly validated certificates and the lowest PAR-2.
These two measurements should be nearly identical, since certificates expected to time out are excluded from the subset.
Mean checking time should increase as Certifaiger's optimizations are removed, with COI being the most essential.
Because the subset focuses on smaller certificates, Caketaiger's formula generation time may be closer to Certifaiger's than in the paper, as the Generation scatter plot also suggests.

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
The sources of Caketaiger (which is part of CakeML) and HOL4 (theorem prover) live in `formalization/`;
Poly/ML (Standard ML compiler/REPL) v5.9.2 is fetched and built by the `Dockerfile`.
As CakeML requires an extensive toolchain to fully build, we also include the assembly code of Caketaiger generated by the CakeML compiler.
Additionally, Caketaiger has been merged into the [CakeML repository](https://github.com/CakeML/cakeml/),
where it is regularly regression tested.

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

### Tool Usage

Caketaiger takes the (binary) AIGER files for the model and the witness, and an optional prefix for the CNF files.
In some cases, it may be necessary to provide the binary with more memory to prevent garbage collection from taking the majority of the time:
  ```bash
  ./caketaiger --CML_HEAP_SIZE=26000 --CML_STACK_SIZE=2000 model.aig witness.aig
  ```

For usage of our other tools, see the respective GitHub pages:

- [Certifaiger](https://github.com/Froleyks/certifaiger)
- [Voiraig](https://github.com/Froleyks/voiraig)

## Formalization

The HOL and CakeML formalizations relevant for the submitted artifact are prebuilt.
Their versions correspond to what has been used to generate the binary artifact.
The latest version of the CakeML formalization can be found on [master](https://github.com/CakeML/cakeml/tree/master/examples/hwmcc_checker),
where many TODOs have been cleaned out and some improvements have been made.

The easiest way to browse the theories is to run:
  ```bash
  cd /app/formalization/cakeml/examples/hwmcc_checker/compilation/proofs
  cat /app/src/load-theories.sml - | hol
  ```

This will drop you into an interactive HOL session and pre-load all of the relevant formalized theory files.

The load takes a while; you should see some output like this:
  ```text
  ---------------------------------------------------------------------
       HOL4 [Trindemossen 2 (stdknl, built Wed Oct 21 03:05:01 2026)]
  
       For introductory HOL help, type: help "hol";
       To exit type <Control>-D
  ---------------------------------------------------------------------
  ...
  Load completed.
  ```

You can then read a proved theorem by sending its name to the HOL terminal, e.g.:

  ```text
  xaig_certTheory.is_witness_xis_safe_and_live;

  Output:
  val it =
   ⊢ is_witness mxaig mreset mnext msafes mcnstrs mqxaig mlive mlatches wxaig
       wreset wnext wsafes wcnstrs wqxaig wlive wlatches ∧
     dep_model mxaig mreset mnext msafes mcnstrs minput mlatches ∧
     dep_qxaig minput mqxaig mlive mlatches ∧
     is_stratified lt wxaig wreset (wlatches DIFF mlatches) ∧ FINITE wlatches ⇒
     xis_safe mxaig mreset mnext mcnstrs mlatches msafes ∧
     xis_live mxaig mreset mnext mcnstrs mqxaig (IMAGE set (set mlive))
       mlatches: thm
  ```

  ```text
  caketaiger_lrupProofTheory.caketaiger_lrup_sound;

  Output:
  val it =
   ⊢ caketaiger_run cl fs mc ms ∧ cnf_files_fresh fs (cl_prefix cl) ∧
     Terminate Success evs ∈ machine_sem mc (basis_ffi ext cl fs) ms ∧
     extract_fs ext (cl,fs) evs = SOME fs₁ ∧ stdout fs init ∧
     stdout fs₁ (init ^ «SUCCESS\n») ∧
     EVERY (λf. ∃txt. file_content fs₁ f = SOME txt ∧ lrup_verified txt)
       (cnf_fnames (cl_prefix cl)) ⇒
     ∃maig mreset mnext msafes mcnstrs mlive mlatches mlatch_start
         mmax_latch.
       get_model fs cl❲1❳ =
       SOME
         (maig,mreset,mnext,msafes,mcnstrs,mlive,mlatches,mlatch_start,
          mmax_latch) ∧
       is_safe maig mreset mnext (set mcnstrs) (set mlatches) (set msafes) ∧
       is_live maig mreset mnext (set mcnstrs) (qleft maig)
         (IMAGE set (set (qleft_live mlive))) (set mlatches): thm
  ```


To do a rebuild of the relevant files, you can first delete the prebuilt theories, then run `Holmake`:
  ```bash
  cd /app/formalization/cakeml/examples/hwmcc_checker/
  Holmake cleanAll
  Holmake
  cd compilation; Holmake
  cd proofs; Holmake
  ```

You should see output like this (some lines omitted).
The "OK" indicates that the proofs were checked with no errors/omissions.
The output has been generated on a laptop with an Intel i5-8265U and 32GB RAM.

  ```text
  ...
  aig_parseTheory                           (18s)   [3/7]     OK
  xaig_certTheory                           (28s)   [4/7]     OK
  xaig_to_cnfTheory                         (30s)   [5/7]     OK
  xaig_cert_encodeTheory                    (44s)   [6/7]     OK
  ...
  caketaigerProgTheory      .../translation (82s)   [6/9]     OK
  caketaigerProgProofTheory .../translation(490s)   [7/9]     OK
  caketaigerARM8CompileTheory ...ompilation(272s)   [8/9]     OK
  caketaigerCompileTheory   .../compilation(275s)   [9/9]     OK
  ...
  caketaigerProofTheory                    (136s)   [1/2]     OK
  caketaiger_lrupProofTheory               (153s)   [2/2]     OK
  ```

### Formalization (glossary)

The relevant contributions are all in the `cakeml/examples/hwmcc_checker/` directory and its subdirectories.

The argument order of `is_next` and `is_inf_trace` in the paper represents the
latest version of the formalization and is slightly different from the one in this artifact.
Additionally,
`get_model` in Fig. 4 of the paper does not return `mlatch_start` and `mmax_latch`,
which are only used for efficient checking of technical conditions,
reflecting the latest version of the formalization.

In the `hwmcc_checker/` folder:

- `aigScript.sml` defines And-Inverter Graphs (Sec. 4.1) and safety/liveness (Sec. 4.2).

- `aig_parseScript.sml` defines the parser for (binary) AIGER files (Sec. 5.1).

- `xaigScript.sml` defines the extended And-Inverter Graphs (Sec. 5.2).

- `xaig_certScript.sml` defines the certificate conditions (Sec. 2.2 and 3) and proves their soundness (Sec. 4.3).
The theorem of interest here is `is_witness_xis_safe_and_live`.
While this theorem is proven over extended AIGs,
the final theorem is a statement over "normal" AIGs.

- `xaig_cert_encodeScript.sml` defines the encoding of the certificate conditions
into xAIGs (Sec. 5.4) and the stratification check (Sec. 5.3).
The theorem of interest is `encoding_xis_safe_and_live`.
The automation mentioned in the paper is `numify_cond`.

- `xaig_to_cnfScript.sml` defines the lowering of xAIG to CNF (Sec. 5.5).
The theorem of interest here is `xaig_to_cnf_correct`.

- `aig_cert_fullScript.sml` assembles the passes described in Fig. 3,
and also checks some technical side conditions (Sec. 5.3).
The theorem of interest here is `process_and_check_return`.
The functions `parse_model` and `preprocess_model` are trusted components.

In the `hwmcc_checker/translation` folder:

- `caketaigerProgScript.sml` combines the definitions that have been translated
in a proof-producing manner from HOL to CakeML into a command-line interface (CLI) program.
The part of interest is the definition of `fun main ()`.

- `caketaigerProgProofScript.sml` proves correctness for the main function.
The theorem of interest is `main_semantics`;
`main_sem` and `make_cert_sem` specify the behavior that we prove that the main function has.
Note that `get_model` is part of the specification as well.

In the `hwmcc_checker/compilation` and `hwmcc_checker/compilation/proofs` folders:

- `caketaiger{,ARM8}CompileScript.sml` compiles caketaiger by (verified) evaluation
inside the logic of HOL.

- `caketaigerProofScript.sml` composes the semantics theorem and the compiler correctness
theorem with the compiler evaluation theorem to produce an end-to-end
correctness theorem that reaches final machine code.
The theorem of interest is `machine_code_sound`.

- `caketaiger_lrupProofScript.sml` composes the end-to-end correctness theorems of caketaiger and of the verified LRUP checker cake_lrup.
The theorem of interest is `caketaiger_lrup_sound` (Sec. 5.6, Fig. 4).


Nils Froleyks
KU Leuven
2026-10-09

Daniel Nezamabadi
Nanyang Technological University
2026-10-21
