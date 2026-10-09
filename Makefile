SHELL := bash
MAKEFLAGS += --no-print-directory
.IGNORE:

NAME := caketaiger
EXPERIMENTS := multi pvs hwmcc
DEPS := multi/witness bin/runlim bin/certifaiger bin/aigsplit bin/aigtoaig bin/aigtocnf bin/cadical bin/caketaiger bin/cake_lrup bin/proveit bin/pvs-sbclisp bin/pvs-theories
GOAL := $(or $(filter all sub smoketest,$(MAKECMDGOALS)),all)

export SUBSET := --sub 28800
sub: export TIME ?= 1000
sub: export MEM_PER_CPU ?= 1400
smoketest: export TIME ?= 10

all smoketest sub: $(EXPERIMENTS)
	rm -rf $@; mkdir -p $@
	cp $(foreach x,$(EXPERIMENTS),$(wildcard $(x)/$(x)-$@*.pdf $(x)/$(x)-$@*.tex)) $@
	./bin/tex.sh $@

.SECONDEXPANSION:
$(EXPERIMENTS): | .venv \
	$$(if $$(wildcard $$@/log-*-$(GOAL)),$(DEPS),$$(if $$(wildcard $$@/data-$(GOAL)),,$(DEPS)))
	$(MAKE) --ignore-errors -C $@ $(GOAL)

$(filter bin/%,$(DEPS)) &:
	$(MAKE) -C src

multi/witness:
	tar -xJf benchmarks.tar.xz

pilot:
	$(MAKE) all TIME=10
	for i in $(EXPERIMENTS); do cp $$i/data-all $$i/our-data; done
benchmarks.tar.xz: multi/model multi/witness pvs/model pvs/nuxmv pvs/voiraig
	tar -I 'xz -9e' -cf $@ $^

CONTAINER ?= $(firstword $(shell command -v podman 2>/dev/null) $(shell command -v docker 2>/dev/null))
container-%: load
	$(CONTAINER) cp Makefile $(NAME):/app
	$(CONTAINER) exec -t -e MAKEFLAGS='$(MAKEFLAGS)' $(NAME) make $*
	$(CONTAINER) cp $(NAME):/app/$*.pdf $*.pdf && echo Copied to $*.pdf
enter: load
	$(CONTAINER) exec -it $(NAME) bash
stop:
	-$(CONTAINER) stop -t 0 $(NAME)
extract: load
	$(CONTAINER) cp $(NAME):/app/. .
load:
	@if $(CONTAINER) image inspect $(NAME) >/dev/null 2>&1; then :; \
	elif [ -f $(NAME).tar.xz ]; then \
		unxz -T0 -k $(NAME).tar.xz; \
		$(CONTAINER) load -i $(NAME).tar; \
		rm $(NAME).tar; \
	else \
		$(CONTAINER) build -t $(NAME) .; \
	fi
	@$(CONTAINER) run -dit --network none --name $(NAME) $(NAME) sleep infinity 2> /dev/null || true
	@$(CONTAINER) start $(NAME)
$(NAME).tar.xz:
	git archive -o /tmp/$(NAME).tar HEAD
	$(CONTAINER) build -t $(NAME) - < /tmp/$(NAME).tar
	rm /tmp/$(NAME).tar
	$(CONTAINER) save -o $(NAME).tar $(NAME)
	xz -T0 $(NAME).tar
$(NAME).zip: $(NAME).tar.xz Makefile readme.md LICENSE
	rm -rf $@ /tmp/$(NAME)-zip
	mkdir -p /tmp/$(NAME)-zip/$(NAME)
	cp $^ /tmp/$(NAME)-zip/$(NAME)/
	cd /tmp/$(NAME)-zip && zip -r $(abspath $@) $(NAME)
	rm -rf /tmp/$(NAME)-zip
	sha256sum $@

# Extract first; submit, then run make again after the jobs finish.
slurm: | $(DEPS) .venv
	for i in $(EXPERIMENTS); do $(MAKE) -C $$i benchmarks; rm -f $$i/data-all; done
	$(MAKE)
export PATH := $(abspath .venv)/bin:$(PATH)
.venv:
	uv venv .venv
	uv pip install pandas matplotlib

clean: stop
	rm -rf all sub smoketest all.pdf sub.pdf smoketest.pdf
	for i in $(EXPERIMENTS); do $(MAKE) -C $$i clean; done
	rm -rf multi/model multi/witness pvs/model pvs/nuxmv pvs/voiraig hwmcc/model hwmcc/witness
	-$(CONTAINER) rm -f $(NAME)
	-$(CONTAINER) rmi -f $(NAME)

.PHONY: $(EXPERIMENTS) stop clean enter extract load container-% pilot
