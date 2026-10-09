#!/usr/bin/env bash
set -euo pipefail

: > benchmarks-caketaiger
group=0
while read -r witness; do
    name=${witness##*/}
    name=${name%.aig}
    group=$((group + 1))
    echo "../bin/run.sh model/${name#*-}.aig $witness @$group caketaiger $name" >> benchmarks-caketaiger
done < <(find witness -name '*.aig' | sort)
