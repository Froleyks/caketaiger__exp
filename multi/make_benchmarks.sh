#!/usr/bin/env bash
set -euo pipefail

: > benchmarks-certifaiger
: > benchmarks-caketaiger
group=0
while read -r witness; do
    name=${witness##*/}
    name=${name%.aig}
    for config in certifaiger caketaiger; do
        group=$((group + 1))
        echo "../bin/run.sh model/${name#*-}.aig $witness @$group $config $name" >> "benchmarks-$config"
    done
done < <(find witness -name '*.aig' | sort)
