#!/usr/bin/env bash
set -euo pipefail

: > benchmarks-caketaiger
: > benchmarks-pvs
group=0
while read -r witness; do
    name=${witness##*/}
    name=${name%.aig}
    [[ -f nuxmv/$name.pvs ]] || continue
    group=$((group + 1))
    echo "../bin/run.sh model/$name.aig $witness @$group caketaiger $name" >> benchmarks-caketaiger
    echo "../bin/run.sh model/$name.aig nuxmv/$name.pvs @$group pvs $name" >> benchmarks-pvs
done < <(find voiraig -name '*.aig' | sort)
