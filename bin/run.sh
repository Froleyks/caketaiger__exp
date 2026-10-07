#!/usr/bin/env bash
# Usage: run.sh model witness @group config name
set -o pipefail
[[ $# == 5 ]] || exit 2
model=$1
witness=$2
group=$3
dir=$4
name=$5

# Claim before scratch setup. Delete the log manually to retry a failed task.
: "${LOG:=$(pwd)/log}"
mkdir -p "$LOG" || exit 1
log="$LOG/${dir}_${name}"
[[ -e "$log.log" ]] && exit 0
if ! (set -o noclobber; : >"$log.log") 2>/dev/null; then
    [[ -e "$log.log" ]] && exit 0
    exit 1
fi
exec 1>>"$log.log" 2>"$log.err"

bin="$(cd -- "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd -P)"
export PATH="$bin:$PATH"
LOG="$(cd -- "$LOG" && pwd -P)"
log="$LOG/${dir}_${name}"
export LIMIT_LOG="$log"
echo "benchmark: $model"
echo "witness: $witness"
echo "group: $group"
echo "dir: $dir"
echo "name: $name"
echo 'status: incomplete'

# Proofs, translated inputs and all tool intermediates stay in scratch.
: "${SCRATCHDIR:=${VSC_SCRATCH:-${TMPDIR:-/var/tmp}}}"
mkdir -p "$SCRATCHDIR/froleyks" || exit 1
TMP=$(mktemp -d "$SCRATCHDIR/froleyks/run-XXXXXXXX") || exit 1
TMP="$(cd -- "$TMP" && pwd -P)"
trap 'res=$?; rm -rf -- "$TMP"; exit "$res"' EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 131' QUIT
trap 'exit 143' TERM
export TMPDIR="$TMP"
cp "$model" "$TMP/model.aig" || exit 1
cp "$witness" "$TMP/witness.${witness##*.}" || exit 1
witness="$TMP/witness.${witness##*.}"
cd "$TMP" || exit 1

t=$(date +%s%N)
case "$dir" in
    certifaiger|certifaiger-*) certifaiger.sh "$TMP/model.aig" "$witness" ;;
    caketaiger) caketaiger.sh "$TMP/model.aig" "$witness" ;;
    pvs) pvs.sh "$witness" ;;
    *) exit 2 ;;
esac
res=$?
t=$(( $(date +%s%N) - t ))
status=error-$res
[[ $res == 0 ]] && status=ok
[[ $res == 124 ]] && status=timeout
memory=0
# Child tools may return a generic error after a resource limit was reached.
for run in "$log"-*.run; do
    [[ -f "$run" ]] || continue
    if grep -qF 'out of time' "$run"; then
        status=timeout
    elif grep -qF 'out of memory' "$run" && [[ $status != timeout ]]; then
        status=memout
    fi
    value=$(sed -n 's/^\[runlim\] space:[[:space:]]*\([0-9][0-9]*\) MB.*$/\1/p' "$run" | tail -n 1)
    [[ -n "$value" ]] && (( value > memory )) && memory=$value
done
printf 'time: %d.%09d\n' "$((t / 1000000000))" "$((t % 1000000000))"
echo "memory: $memory"
echo "status: $status"
[[ $status == ok ]]
