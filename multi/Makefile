SHELL := bash
.IGNORE:
-include ../config.mk

CONFIGS := caketaiger
PARSING := @ time: @ status: @ memory: @ t_generation: generation @ t_split: split \
	$(foreach check,Reset Transition Safety Liveness Base Inductive Decrease Closure Consistent,@ t_cnf-$(check): cnf_$(check) @ t_$(check): solve_$(check) @ t_check-$(check): check_$(check)) \
	@ 'size model ' model_format 6 model_M 7 model_I 8 model_L 9 model_O 10 model_A 11 model_B 12 model_C 13 model_J 14 model_F 15 \
	@ 'size witness ' witness_format 6 witness_M 7 witness_I 8 witness_L 9 witness_O 10 witness_A 11 witness_B 12 witness_C 13 witness_J 14 witness_F 15 \
	$(foreach check,Reset Transition Safety Liveness Base Inductive Decrease Closure Consistent,@ 'size CNF $(check) ' vars_$(check) 8 clauses_$(check) 9)

BENCHMARKS := $(foreach goal,all sub smoketest,$(addsuffix -$(goal),$(addprefix benchmarks-,$(CONFIGS))))

all sub smoketest: %: data-% | model
	./plot.py $< $(notdir $(CURDIR))-$@

model:
	tar -xJf ../benchmarks.tar.xz -C .. multi/model

data-%: LOG = $(addsuffix -$*,$(addprefix log-,$(CONFIGS)))
.SECONDEXPANSION:
data-%: $$(if $$(wildcard $$(LOG)),$$(LOG),$$(if $$(wildcard $$@),,$$(LOG)))
	../bin/parse.py $^ $(PARSING) > $@

log-%: benchmarks-% FORCE
	../bin/parallel.sh benchmarks-$* log-$*

benchmarks: $(BENCHMARKS)
$(BENCHMARKS) &: make_benchmarks.sh Makefile ../Makefile
	rm -f benchmarks-*
	./$<
	../bin/pack.py our-data benchmarks-*
	for i in benchmarks-*; do \
		cp $$i $$i-sub; \
		mv $$i $$i-all; \
		grep -E ' (stable-lmcs06counter0|k-cucnt3)$$' $$i-all > $$i-smoketest; \
	done
	../bin/pack.py our-data benchmarks-*-smoketest
	../bin/pack.py our-data benchmarks-*-sub $(SUBSET)

clean:
	rm -rf benchmarks-* log-* data-* *.pdf *.tex

FORCE:
.PHONY: all sub smoketest benchmarks clean FORCE
