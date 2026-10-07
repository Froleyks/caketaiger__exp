#!/usr/bin/env bash
set -euo pipefail
# Runs benchmark commands in parallel.
# Benchmark files list commands followed by "@group tool benchmark"
# where tool_benchmark is a unique identifier (checked below) and
# group determines which benchmarks are run sequentially
# (same group) or in parallel (different groups).

benchmarks=${1:-benchmarks}
log=${2:-"log-$(basename "$(pwd)")"}
name=${3:-"$(basename "$(pwd)")"}
CPUS=${CPUS:-1}

bin="$(cd -- "$(dirname -- "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd -P)"
PATH="$bin:$PATH"

[[ -f "$benchmarks" ]] || {
    printf 'error: benchmarks file not found: %s\n' "$benchmarks" >&2
    exit 1
}
# trim leading/trailing whitespace in-place
sed -i -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' "$benchmarks"

# detect duplicate ids (last two whitespace-separated fields joined by "_")
duplicates="$(awk '{
      id=$(NF-1) "_" $NF
      if (id in x) {
        if (x[id] != "") print x[id]
        print
        x[id] = ""
      } else {
        x[id] = $0
      }
    }' "$benchmarks" | sort)"
[[ -z "$duplicates" ]] || {
    printf 'error: duplicate ids\n%s\n' "$duplicates" >&2
    exit 1
}

if ! [[ -d "$log" ]]; then
    mkdir -p "$log"
    {
        printf '%s\n' "$(realpath "$benchmarks")"
        printf '%s benchmarks\n' "$(wc -l <"$benchmarks")"
        printf 'TIME: %s\n' "${TIME:-UNLIMITED}"
        printf 'SPACE: %s\n' "${SPACE:-UNLIMITED}"
        printf 'CPUS: %s\n' "$CPUS"
        printf 'hostname: %s\n\n' "$(hostname)"
        printf 'Nils Froleyks\nKU Leuven\n%s\n' "$(date +"%Y-%m-%d %H:%M %Z")"
    } >"$log/Readme"
fi

mkdir -p "$log"
ts="$(date +"%Y%m%dT%H%M%S")"

refresh_log_cache() {
    local log="$1"
    local list="$log/.parallel-logs"
    local stamp="$log/.parallel-logs-stamp"
    local before after
    before="$(stat -L -c '%y' -- "$log")" || return
    if [[ -f "$list" && -f "$stamp" && "$(<"$stamp")" == "$before" ]]; then
        return 0
    fi

    # Create both cache files before taking the snapshot. Updating them in
    # place does not change the directory timestamp; replacing them would.
    # Clear the stamp first so an interrupted rebuild cannot be reused.
    : >"$stamp" || return
    : >"$list" || return
    before="$(stat -L -c '%y' -- "$log")" || return
    # Read names only: -type f can trigger a metadata lookup for every entry
    # on network filesystems. A matching .log name marks a benchmark complete.
    find -H "$log" -mindepth 1 -maxdepth 1 -name '*.log' -printf '%f\n' >"$list" || return
    after="$(stat -L -c '%y' -- "$log")" || return
    if [[ "$before" == "$after" ]]; then
        printf '%s\n' "$before" >"$stamp"
    fi
}

all_logs_present() {
    local benchmarks="$1"
    local list="$2"
    awk 'FILENAME == ARGV[1] {
        sub(/\.log$/, "", $0)
        done[$0]=1
        next
    } {
        id=$(NF-1) "_" $NF
        if (!(id in done)) exit 1
    }' "$list" "$benchmarks"
}

remaining_benchmarks() {
    # Keep only benchmarks that don't already have a corresponding log.
    local benchmarks="$1"
    local log="$2"
    local remaining="$log/benchmarks-$ts"
    # The post-run check must not truncate the file it is about to read.
    [[ "$benchmarks" != "$remaining" ]] || remaining="$remaining-remaining"
    refresh_log_cache "$log" || return
    awk ' FILENAME == ARGV[1] {
            sub(/\.log$/,"",$0)
            done[$0]=1
            next
        } {
            id=$(NF-1) "_" $NF
            if (!(id in done)) print
        } ' "$log/.parallel-logs" "$benchmarks" >"$remaining" || return
    printf '%s\n' "$remaining"
}

completed() {
    local benchmarks="$1"
    if [[ ! -s "$benchmarks" ]]; then
        rm -f -- "$benchmarks"
        return 0
    fi
    return 1
}

touch_log_directory() {
    local log="$1"
    local stamp="$log/.parallel-logs-stamp"
    local before
    before="$(stat -L -c '%y' -- "$log")" || return
    if [[ -f "$stamp" && "$(<"$stamp")" == "$before" ]]; then
        # Make must see a newer log directory even when the cache was reused.
        # Carry a valid cache forward to the timestamp caused by our touch.
        touch -- "$log" "$stamp" || return
        stat -L -c '%y' -- "$log" >"$stamp"
    else
        # Bookkeeping or new logs may have invalidated the cached list.
        touch -- "$log" "$stamp" || return
        : >"$stamp"
    fi
}
trap 'touch_log_directory "$log"' EXIT

# Check before creating bookkeeping files, which would invalidate the cache.
refresh_log_cache "$log"
all_logs_present "$benchmarks" "$log/.parallel-logs" && exit 0

benchmarks="$(remaining_benchmarks "$benchmarks" "$log")"
completed "$benchmarks" && exit 0

n="$(wc -l <"$benchmarks" | tr -d '[:space:]')"
if [[ "$n" -eq 0 ]]; then
    printf 'Complete %s\n' "$log"
    rm -f "$benchmarks"
    exit 0
fi

# Collect distinct numeric group ids (in first-seen order)
group_ids_file="$log/group-ids-$ts"
awk '
  match($0, / @[0-9]+ /) {
    g = substr($0, RSTART+2, RLENGTH-3) + 0
    if (!(g in seen)) { seen[g]=1; order[++n]=g }
  }
  END { for (i=1;i<=n;i++) print order[i] }
' "$benchmarks" >"$group_ids_file"
groups="$(wc -l <"$group_ids_file" | tr -d "[:space:]")"
array_spec="$(paste -sd, "$group_ids_file")"

LOG="$(cd -- "$log" && pwd -P)"
export LOG
banner="parallel.sh running $n benchmarks in $groups groups with $CPUS cpus each${TIME:+ for ${TIME}s}${SPACE:+ with ${SPACE}MB}"
if command -v sbatch >/dev/null 2>&1; then
    printf "$banner using slurm\n"
    [ -z "${WAIT+x}" ] || echo Waiting for result...
    mkdir -p "$log/slurm"

    max_jobs=500
    already_in_queue="$(squeue -M mindwell -h -t pending,running -r | wc -l)"
    capacity=$((max_jobs - 5 - already_in_queue))
    ((capacity <= 0)) && {
        printf 'Reached capacity %s\n' "$max_jobs" >&2
        exit 1
    }
    if ((groups > capacity)); then
        echo "Exceeding capacity, $already_in_queue / $max_jobs queued, only submitting $capacity groups"
        keep_ids="$log/group-ids-$ts-keep"
        head -n "$capacity" "$group_ids_file" >"$keep_ids"
        remaining="$log/benchmarks-$ts-slurm"
        awk '
            FNR==NR { keep[$1]=1; next }
            match($0, / @[0-9]+ /) {
                g = substr($0, RSTART+2, RLENGTH-3) + 0
                if (keep[g]) print
                next
            }
            { print }
            ' "$keep_ids" "$benchmarks" >"$remaining"
        benchmarks="$remaining"
        mv "$keep_ids" "$group_ids_file"
        groups="$capacity"
        array_spec="$(paste -sd, "$group_ids_file")"
    fi

    ARRAY="$log/array.sh"
    array_spec="0-$((groups - 1))"
    {
        printf "#!/bin/sh\n"
        printf "set -eu\n"
        printf "%s\n" "export PATH=\"$bin:\$PATH\""
        printf "%s\n" "${TIME:+export TIME=$TIME}"
        printf "%s\n" "${SPACE:+export SPACE=$SPACE}"
        printf "%s\n" "export LOG=$LOG"
        printf '%s\n' "group=\$(sed -n \"\$((\${SLURM_ARRAY_TASK_ID:?} + 1))p\" \"$group_ids_file\")"
        printf "%s\n" "grep -F \" @\${group:?} \" \"$benchmarks\" | while IFS= read -r line; do bash -c \"\$line\"; done"
    } >"$ARRAY"
	secs=$(( ${TIME:-86400} * ${SLACK:-105} / 100 ))
	printf -v time '%d-%02d:%02d:%02d' \
	  $(( secs / 86400 )) \
	  $(( (secs % 86400) / 3600 )) \
	  $(( (secs % 3600) / 60 )) \
	  $(( secs % 60 ))
	echo Slurm limit $time
    sbatch ${SLURM:-} \
        ${WAIT:+--wait} \
        --chdir="$PWD" \
        --time=$time \
        --job-name="$name" \
        --array="$array_spec" \
        --cpus-per-task="$CPUS" \
        --output="$LOG/slurm/$ts-%a.slog" \
        --error="$LOG/slurm/$ts-%a.serr" \
        --parsable \
        "$ARRAY"

elif command -v parallel >/dev/null 2>&1; then
    printf "$banner using parallel\n"
	jobs=$(($(parallel --number-of-cores) / CPUS))
    (( jobs < 1 )) && jobs=1
    group_runner="$log/group-runner-$ts.sh"
    cat >"$group_runner" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
benchmarks="$1"
g="$2"
status=0
# A failed check must not prevent later benchmarks in its group from running.
while IFS= read -r line; do
    bash -c "$line" || status=$?
done < <(awk -v g="$g" '
  match($0, / @[0-9]+ /) {
    line_g = substr($0, RSTART+2, RLENGTH-3) + 0
    if (line_g == g) print
  }
' "$benchmarks")
exit "$status"
EOF
    awk '
        match($0, / @[0-9]+ /) {
            g = substr($0, RSTART+2, RLENGTH-3) + 0
            if (!(g in seen)) { seen[g]=1; order[++n]=g }
        }
     END { for (i=1;i<=n;i++) print order[i] }
    ' "$benchmarks" |
	parallel --bar --jobs "$jobs" --will-cite -- bash "$group_runner" "$benchmarks" {}
    rm -f -- "$group_runner"

    benchmarks="$(remaining_benchmarks "$benchmarks" "$log")"
    completed "$benchmarks"
elif command -v xargs >/dev/null 2>&1; then
    printf "$banner using xargs\n"
    cores=$(
	getconf _NPROCESSORS_ONLN 2>/dev/null ||
	    nproc 2>/dev/null ||
	    sysctl -n hw.ncpu 2>/dev/null ||
	    echo 1
	 )
    jobs=$(( cores / CPUS ))
    (( jobs < 1 )) && jobs=1
    awk '
        match($0, / @[0-9]+ /) {
            g = substr($0, RSTART+2, RLENGTH-3) + 0
            if (!(g in seen)) { seen[g]=1; order[++n]=g }
        }
     END { for (i=1;i<=n;i++) print order[i] }
    ' "$benchmarks" |
	xargs -r -n 1 -P "$jobs" bash -c '
    benchmarks="$1"
    g="$2"
    awk -v g="$g" "
      match(\$0, / @[0-9]+ /) {
        line_g = substr(\$0, RSTART+2, RLENGTH-3) + 0
        if (line_g == g) print
      }
    " "$benchmarks" |
      while IFS= read -r line; do
        bash -c "$line"
      done
  ' _ "$benchmarks"

    benchmarks="$(remaining_benchmarks "$benchmarks" "$log")"
    completed "$benchmarks"
else
    printf "$banner sequentially\n"
    while read -r args; do
        eval "$args"
    done <"$benchmarks"
    benchmarks="$(remaining_benchmarks "$benchmarks" "$log")"
    completed "$benchmarks"
fi
