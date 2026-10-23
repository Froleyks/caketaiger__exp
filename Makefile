SHELL := bash
MAKEFLAGS += --no-print-directory
.IGNORE:

NAME := caketaiger
EXPERIMENTS := multi pvs hwmcc
DEPS := multi/witness bin/runlim bin/certifaiger bin/aigsplit bin/aigtoaig bin/aigtocnf bin/cadical bin/caketaiger bin/cake_lrup bin/proveit bin/pvs-sbclisp bin/pvs-theories
GOAL := $(or $(filter all sub smoketest,$(MAKECMDGOALS)),all)

# ADJUST THIS To YOUR HARDWARE!
sub: export MEM_PER_CPU ?= 1500
sub: export CPUS ?= 2
sub: export TIME ?= 3600
export SUBSET := --sub 28800

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

dry: | .venv multi/witness
	for i in $(EXPERIMENTS); do \
		$(MAKE) -C $$i benchmarks; \
		./bin/pack.py $$i/our-data $$i/benchmarks-*-sub* --dry $$i/data-sub; \
	done; $(MAKE) sub

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
ARCH ?= $(if $(filter arm64 aarch64,$(shell uname -m)),arm,amd)
load:
	@if $(CONTAINER) image inspect $(NAME) >/dev/null 2>&1; then :; \
	elif [ -f $(NAME)-$(ARCH).tar.xz ]; then \
		unxz -T0 -k $(NAME)-$(ARCH).tar.xz; \
		$(CONTAINER) load -i $(NAME)-$(ARCH).tar; \
		rm $(NAME)-$(ARCH).tar; \
		$(CONTAINER) tag $(NAME):$(ARCH) $(NAME); \
	else \
		$(CONTAINER) build -t $(NAME) .; \
	fi
	@$(CONTAINER) run -dit --network none --name $(NAME) $(NAME) sleep infinity 2> /dev/null || true
	@$(CONTAINER) start $(NAME)
IMAGES := $(NAME)-arm.tar.xz $(NAME)-amd.tar.xz
$(IMAGES): $(NAME)-%.tar.xz:
	git archive -o /tmp/$(NAME)-$*.tar HEAD
	for i in hwmcc/hwmcc25-benchmarks-bitlevel-safety.tar.gz hwmcc/hwmcc25-logfiles.tar.gz; do \
		if [ -f "$$i" ]; then tar -rf /tmp/$(NAME)-$*.tar "$$i"; fi; \
	done
	$(CONTAINER) build --platform linux/$*64 -t $(NAME):$* - < /tmp/$(NAME)-$*.tar
	rm /tmp/$(NAME)-$*.tar
	$(CONTAINER) save -o $(NAME)-$*.tar $(NAME):$*
	xz -T0 $(NAME)-$*.tar
$(NAME).zip: $(IMAGES) $(IMAGES:.tar.xz=-build.log) Makefile readme.md LICENSE
	rm -rf $@ /tmp/$(NAME)-zip
	mkdir -p /tmp/$(NAME)-zip/$(NAME)
	cp $(filter-out Makefile readme.md LICENSE,$^) /tmp/$(NAME)-zip/$(NAME)/
	git archive --format=tar HEAD Makefile readme.md LICENSE | tar -xf - -C /tmp/$(NAME)-zip/$(NAME)
	cd /tmp/$(NAME)-zip && zip -r $(abspath $@) $(NAME)
	rm -rf /tmp/$(NAME)-zip
	awk -v hash="$$(sha256sum "$@" | cut -d ' ' -f 1)" '\
		/^## Quickstart$$/ { state = 1 } \
		state == 1 && /^```bash$$/ { \
			print; print "echo " hash "  $@ | sha256sum -c -"; \
			print "unzip $@ && cd $(NAME)"; state = 2; next \
		} \
		state == 2 && /^make[ \t]/ { state = 3 } \
		state != 2 { print } \
		END { if (state != 3) exit 1 }' readme.md > readme.md.tmp && mv readme.md.tmp readme.md

# Extract first; submit, then run make again after the jobs finish.
slurm: | $(DEPS) .venv
	for i in $(EXPERIMENTS); do $(MAKE) -C $$i benchmarks; rm -f $$i/data-all; done
	$(MAKE)
export PATH := $(abspath .venv)/bin:$(PATH)
.venv:
	uv venv .venv
	uv pip install pandas matplotlib
our-data:
	for i in $(EXPERIMENTS); do cp $$i/our-data $$i/data-all; done
clean: stop
	rm -rf all sub smoketest all.pdf sub.pdf smoketest.pdf
	for i in $(EXPERIMENTS); do $(MAKE) -C $$i clean; done
	rm -rf multi/model multi/witness pvs/model pvs/nuxmv pvs/voiraig hwmcc/model hwmcc/witness
	-$(CONTAINER) rm -f $(NAME)
	-$(CONTAINER) rmi -f $(NAME) $(NAME):arm $(NAME):amd

.PHONY: $(EXPERIMENTS) stop clean enter extract load container-% pilot dry our-data
