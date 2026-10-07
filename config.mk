# TIME (seconds) and SPACE (MB) are enforced by bin/limit.sh using runlim.
# CPUS is cores per task; MEM_PER_CPU is MB per allocated core.
# SLACK is the Slurm wall-time percentage of TIME.
NAME ?= caketaiger
TIME ?= 3600
MEM_PER_CPU ?= 4000
CPUS ?= 32
SLACK ?= 205
CLUSTER ?= mindwell
PARTITION ?= batch_graniterapids
ACCOUNT ?= lp_certifox

SLURM ?= \
	$(if $(CPUS),--cpus-per-task=$(CPUS)) \
	$(if $(MEM_PER_CPU),--mem-per-cpu=$(MEM_PER_CPU)) \
	$(if $(CLUSTER),--cluster=$(CLUSTER)) \
	$(if $(PARTITION),--partition=$(PARTITION)) \
	$(if $(ACCOUNT),--account=$(ACCOUNT))
SPACE ?= $(shell echo $$(( ($(CPUS) * $(MEM_PER_CPU)) - 400 )))
export NAME TIME MEM_PER_CPU CPUS SLACK CLUSTER PARTITION ACCOUNT SLURM SPACE
