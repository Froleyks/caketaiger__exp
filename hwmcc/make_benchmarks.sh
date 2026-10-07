#!/usr/bin/env bash
set -euo pipefail

for config in certifaiger certifaiger-plain certifaiger-coi certifaiger-coi+xor certifaiger-coi+xor+ite caketaiger; do
    : > "benchmarks-$config"
done
group=0
while read -r witness; do
    model=${witness#*/bitlevel_safety/}
    model=${model%/certificate.unsat}
    name=${witness#witness/}
    name=${name%/certificate.unsat}
    name=${name//\//_}
    for config in certifaiger certifaiger-plain certifaiger-coi certifaiger-coi+xor certifaiger-coi+xor+ite caketaiger; do
        case "$config" in
            certifaiger-plain) options="--no-coi --no-xor --no-ite --no-pg" ;;
            certifaiger-coi) options="--no-xor --no-ite --no-pg" ;;
            certifaiger-coi+xor) options="--no-ite --no-pg" ;;
            certifaiger-coi+xor+ite) options="--no-pg" ;;
            *) options="" ;;
        esac
        group=$((group + 1))
        echo "${options:+AIGTOCNF_OPTIONS='$options' }../bin/run.sh model/$model $witness @$group $config $name" >> "benchmarks-$config"
    done
done < <(find witness -name certificate.unsat | sort)
