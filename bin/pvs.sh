#!/usr/bin/env bash
set -euo pipefail
bin=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
tmp=$(realpath "$(mktemp -d "${TMPDIR:-/tmp}/pvs-XXXXXXXX")")
trap 'rm -rf -- "$tmp"' EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
# Old KU translations name the theory after their original output file.
theory=$(sed -nE 's/^([A-Za-z][A-Za-z0-9_]*)\[.*: THEORY[[:space:]]*$/\1/p' "$1" | head -1)
[[ -n "$theory" ]] || { echo 'Missing PVS certificate theory name' >&2; exit 1; }
cp "$1" "$tmp/$theory.pvs"
# Shared checker theories and proofs belong only in the temporary context.
cp "$bin/pvs-theories/"* "$tmp/"
cd "$tmp"

if [[ -f "$bin/pvs.sif" ]]; then
    "$bin/limit.sh" total apptainer exec --cleanenv --bind "$tmp:$tmp" \
        --pwd "$tmp" "$bin/pvs.sif" /opt/pvs/proveit -l "$tmp@${theory}.thm_inv"
else
    "$bin/limit.sh" total "$bin/proveit" -l "$tmp@${theory}.thm_inv"
fi
# Without -i, imported theories are not rechecked: PVS may report incomplete.
grep -E '^[[:space:]]*thm_inv[.]+proved - (incomplete|complete)[[:space:]]' "$theory.thm_inv.summary"
awk '
    /[.]+proved - (incomplete|complete)[[:space:]]/ { proved++ }
    /^Grand Totals:/ {
        totals++
        valid = ($3 > 0 && $3 == $5 && $3 == $7 && $3 == proved &&
                 $4 == "proofs," && $6 == "attempted," && $8 == "succeeded")
    }
    END { exit !(totals == 1 && valid) }
' "$theory.thm_inv.summary"
echo 'check_pvs: thm_inv proved'
