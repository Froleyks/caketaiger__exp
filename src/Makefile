SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.ONESHELL:
bin := $(abspath ../bin)

all: $(bin)/certifaiger $(bin)/aigsplit $(bin)/aigtoaig $(bin)/aigtocnf \
	$(bin)/cadical $(bin)/runlim $(bin)/caketaiger $(bin)/cake_lrup $(bin)/tectonic $(bin)/proveit $(bin)/pvs-theories

aiger:
	$(call clone,aiger,https://github.com/arminbiere/aiger.git,039ec1a2cc37d3093ac35c4b6df65336b346f409)
cadical:
	$(call clone,cadical,https://github.com/arminbiere/cadical.git,c60730422e758ef1cebe7aeddf2dda31c996bf04)
certifaiger:
	$(call clone,certifaiger,https://github.com/Froleyks/certifaiger.git,29d6d3fe4cbac4b9fb6535326c8caf01ff2bd1a4)
runlim:
	$(call clone,runlim,https://github.com/arminbiere/runlim.git,188f1e07fa233b787589900e0184092b49167706)

$(bin)/certifaiger: certifaiger aiger
	cmake -S certifaiger -B certifaiger/build -DCMAKE_BUILD_TYPE=Release \
		-DSTATIC=ON -DCHECK=OFF -DAIGER_DIR=$(abspath aiger)
	cmake --build certifaiger/build
	cp certifaiger/build/certifaiger $@

$(bin)/aigsplit $(bin)/aigtoaig $(bin)/aigtocnf &: aiger
	cd aiger
	./configure.sh -static
	$(MAKE) aigsplit aigtoaig aigtocnf
	cp aigsplit aigtoaig aigtocnf $(bin)/

$(bin)/cadical: cadical
	cd cadical
	./configure -static
	$(MAKE)
	cp build/cadical $(bin)/

$(bin)/runlim: runlim
	cd runlim
	CC='gcc -static' ./configure.sh
	$(MAKE) runlim
	cp runlim $(bin)/

caketaiger-artifacts.tar.xz:
	rm -rf caketaiger-artifacts
	git clone git@github.com:dnezam/cake_tiger-artifacts.git caketaiger-artifacts
	git -C caketaiger-artifacts log -1 --format=fuller --date=iso-strict
	git -C caketaiger-artifacts archive --format=tar --prefix=caketaiger-artifacts/ HEAD | xz > $@
	rm -rf caketaiger-artifacts

$(bin)/caketaiger $(bin)/cake_lrup &: caketaiger-artifacts.tar.xz
	tar -xf caketaiger-artifacts.tar.xz
	$(MAKE) -C caketaiger-artifacts LDLIBS="$(LDLIBS) -static"
	cp caketaiger-artifacts/{caketaiger,cake_lrup} $(bin)/

$(bin)/tectonic:
	curl -fL --retry 3 -o tectonic.tar.gz https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%400.17.0/tectonic-0.17.0-x86_64-unknown-linux-musl.tar.gz
	tar -xzf tectonic.tar.gz tectonic
	install -m755 tectonic $@

$(bin)/proveit $(bin)/pvs-theories &: pvs.tar.xz
	tar -xJf $< nuxmv/PVS \
		nuxmv/Certifying_Rlive_25/PVS_theories/rlive_theories_andproofs_certificates
	mkdir -p $(bin)/pvs-theories
	cp nuxmv/Certifying_Rlive_25/PVS_theories/rlive_theories_andproofs_certificates/{*.pvs,*.prf,pvs-strategies} $(bin)/pvs-theories/
	cd nuxmv/PVS
	unset SBCL_HOME
	./configure
	$(MAKE) -j1
	$(MAKE) -j1
	ln -sf ../src/nuxmv/PVS/proveit $(bin)/proveit

portable: $(bin)/pvs.sif
$(bin)/pvs.sif: pvs.def pvs.tar.xz
	apptainer build $@.tmp pvs.def
	mv $@.tmp $@

define clone
	git clone --no-checkout $(2) $(1)
	git -C $(1) fetch --depth 1 origin $(3)
	git -C $(1) checkout --detach $(3)
endef

clean:
	rm -rf aiger cadical certifaiger runlim caketaiger-artifacts tectonic tectonic.tar.gz nuxmv

.PHONY: all clean portable
