#!/usr/bin/env bash
set -euo pipefail

: > benchmarks-certifaiger
: > benchmarks-caketaiger
: > benchmarks-pvs
group=0
while read -r witness; do
    name=${witness##*/}
    name=${name%.aig}
    for config in certifaiger caketaiger; do
        group=$((group + 1))
        echo "../bin/run.sh model/$name.aig $witness @$group $config $name" >> "benchmarks-$config"
    done
done < <(find voiraig -name '*.aig' | sort)
while read -r witness; do
    name=${witness##*/}
    name=${name%.pvs}
    group=$((group + 1))
    echo "../bin/run.sh model/$name.aig $witness @$group pvs $name" >> benchmarks-pvs
done < <(find nuxmv -maxdepth 1 -name '*.pvs' | sort)
