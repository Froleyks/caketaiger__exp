#!/usr/bin/env bash
# From Certifaiger scripts/check_unsat.in at 27d526e3e979074c3e92582768f577dc6eddb0da.
: "${SAT_OPTIONS:= --quiet --unsat}"
SAT_OPTIONS+=" --no-witness"
bin="$(cd -- "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd -P)"
limit="$bin"/limit.sh
caketaiger="$bin"/caketaiger
sat_solver="$bin/cadical"
sat_checker="$bin/cake_lrup"
echo "$(basename "$0"): Checking with SAT solver $(basename "$sat_solver") $SAT_OPTIONS"
[ -n "$sat_checker" ] && echo "$(basename "$0"): Checking proofs with $(basename "$sat_checker")"
aigtoaig="$bin"/aigtoaig
[ $# -lt 2 ] && echo "usage: $(basename "$0") <model> <witness>" && exit 0
mkdir -p ${TMPDIR:-/tmp}/froleyks-caketaiger
: ${SEQUENTIAL:=false}
TMP=$(mktemp -d "${TMPDIR:-/tmp}"/froleyks-caketaiger/$(basename "$0")-XXXXXXXX)

main_PID=$BASHPID
cleanup() {
	st=$?
	if [[ $BASHPID -eq $main_PID ]]; then
		rm -rf -- "$TMP"
	fi
	exit "$st"
}
trap cleanup EXIT HUP INT QUIT TERM

model="$1"
witness="$2"
shift 2

for f in model witness; do
	path="${!f}"
	[ -f "$path" ] || {
		echo "$(basename "$0"): Error: missing file $path" >&2
		exit 1
	}
	echo "$(basename "$0"): size $f $path $(wc -l <"$path") lines $(wc -c <"$path") bytes $(head -n 1 "$path")"
done

echo $(basename "$0"): Checking witness circuit "$witness"
$limit convert-model $aigtoaig "$model" "$TMP/model.aig" || exit 1
$limit convert-witness $aigtoaig "$witness" "$TMP/witness.aig" || exit 1
cd "$TMP" || exit 1
$limit generation \
	$caketaiger --CML_HEAP_SIZE=26000 --CML_STACK_SIZE=2000 \
	model.aig witness.aig "$@"
caketaiger_exit=$?
[ $caketaiger_exit -ne 0 ] && echo "$(basename "$0"): Error: Caketaiger failed with exit code $caketaiger_exit" >&2 && exit 1

# Match Certifaiger's obligation names for the shared result columns.
mv reset.cnf Reset.cnf || exit 1
mv transition.cnf Transition.cnf || exit 1
mv safety.cnf Safety.cnf || exit 1
mv liveness.cnf Liveness.cnf || exit 1
mv base.cnf Base.cnf || exit 1
mv induction.cnf Inductive.cnf || exit 1
mv decrease.cnf Decrease.cnf || exit 1
mv closure.cnf Closure.cnf || exit 1
mv stable.cnf Consistent.cnf || exit 1

sat() {
	echo Checking $1
	local t
	path="${TMP}/$2"
	echo "$(basename "$0"): size CNF $1 $path $(wc -l <"$path") lines $(wc -c <"$path") bytes $(head -n 1 "$path")"
	if [ -n "$sat_checker" ]; then
		format="--lrat --binary --no-factor"
		expected=0

		proof="${TMP}/$2.proof"
		mkfifo "$proof" || {
			echo "$(basename "$0"): Error: could not create proof FIFO $proof" >&2
			exit 1
		}
		$limit "$1" \
			$sat_solver $SAT_OPTIONS $format "${TMP}/$2" "$proof" &
		solver_pid=$!
		$limit "check-$1" \
			$sat_checker --CML_HEAP_SIZE=26000 --CML_STACK_SIZE=2000 \
			"${TMP}/$2" "$proof" > "${TMP}/$2.check"
		checker_res=$?
		cat "${TMP}/$2.check"
		# CakeLRUP can return zero on errors; require its verification result.
		grep -qxF 's VERIFIED UNSAT' "${TMP}/$2.check" || checker_res=1
		wait "$solver_pid"
		solver_res=$?
		if [ $solver_res -ne 20 ]; then
			echo "Error: $1 check failed"
			exit 1
		fi
		if [ $checker_res -ne $expected ]; then
			echo "Error: $1 proof check failed"
			exit 1
		fi
		rm -f "$proof"
	else
		$limit "$1" \
			$sat_solver $SAT_OPTIONS "${TMP}/$2"
		if [ $? -ne 20 ]; then
			echo "Error: $1 check failed"
			exit 1
		fi
	fi
}

PIDS=()
t="$(date +%s%N)"
for cnf in "$TMP"/*.cnf; do
	base="$(basename "$cnf")"
	name="${base%.cnf}"
	if $SEQUENTIAL; then
		sat "$name" "$base" || {
			echo $(basename "$0"): Certificate check failed.
			exit 1
		}
	else
		(sat "$name" "$base") &
		PIDS+=($!)
	fi
done
res=0
for pid in "${PIDS[@]}"; do
	wait "$pid" || res=1
done
t="$(($(date +%s%N) - t))"
t="$(printf '%d.%09d' "$((t / 1000000000))" "$((t % 1000000000))")"
echo "$(basename "$0"): t_total: $t"
[ $res -ne 0 ] && exit 1
echo "$(basename "$0"): Certificate check passed"
