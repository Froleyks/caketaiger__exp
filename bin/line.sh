#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   parse [-f FILE] [-s SEP] [-p PLACEHOLDER] "kw1&kw2&...&CUTMARK" idx [idx...]
#
# - All keywords (kw1..CUTMARK) must appear in the same line.
# - CUTMARK (the last keyword after '&') is the anchor: output fields are taken
#   from the text AFTER the *last occurrence* of CUTMARK on that line.
# - Indices are 1-based “words” (whitespace-separated) in that remainder.
# - Prints with printf semantics: NO trailing newline.

file="${PARSE_FILE:-}"
sep=" "
placeholder="NaN"

usage() {
  cat >&2 <<'EOF'
Usage:
  parse.sh [-f FILE] [-s SEP] [-p PLACEHOLDER] SPEC IDX...

Notes:
  - SPEC is "kw1&kw2&...&ANCHOR" where ANCHOR is the last '&'-segment.
  - The script prints: SEP + each requested field (no trailing newline).
  - If -f is omitted, reads from stdin.

Example:
  ./parse.sh -f log.log "btor&unsat: size witness " 2 4 7
EOF
}

print_placeholders() {
  local _
  for _ in "$@"; do
    printf '%s%s' "$sep" "$placeholder"
  done
}

# options
while [[ $# -gt 0 ]]; do
  case "$1" in
    -f|--file)
      if [[ $# -lt 2 ]]; then
        usage
        exit 0
      fi
      file="$2"
      shift 2
      ;;
    -s|--sep)
      if [[ $# -lt 2 ]]; then
        usage
        exit 0
      fi
      sep="$2"
      shift 2
      ;;
    -p|--placeholder)
      if [[ $# -lt 2 ]]; then
        usage
        exit 0
      fi
      placeholder="$2"
      shift 2
      ;;
    -h|--help) usage; exit 0 ;;
    --) shift; break ;;
    *) break ;;
  esac
done

spec="${1:-}"
shift || true
[[ -z "$spec" ]] && { usage; exit 0; }

idx_argv=("$@")
idxs="$*"

# Split kw1&kw2&...&ANCHOR
IFS='&' read -r -a kw <<< "$spec"
anchor="${kw[${#kw[@]}-1]}"

# Join keywords with a rarely-used delimiter so awk can split them reliably.
IFS=$'\034' kw_joined="${kw[*]}"
IFS=$' \t\n'

if [[ -n "$file" && ! -r "$file" ]]; then
  print_placeholders "${idx_argv[@]}"
  exit 0
fi

# Awk enforces all keywords, cuts after the final anchor, and prints placeholders
# when the file is missing/unreadable, no line matches, or fields are missing.
awk -v KW="$kw_joined" -v ANCHOR="$anchor" -v IDXS="$idxs" -v SEP="$sep" -v PH="$placeholder" '
  BEGIN {
    n_kw  = split(KW,   K, "\034")
    n_idx = split(IDXS, I, /[[:space:]]+/)
    found = 0
  }
  {
    # Require all keywords
    for (i=1; i<=n_kw; i++) if (index($0, K[i]) == 0) next

    # Cut after the *last occurrence* of ANCHOR
    pos = 0
    start = 1
    while ((j = index(substr($0, start), ANCHOR)) > 0) {
      pos = start + j - 1
      start = pos + length(ANCHOR)
    }

    rest = substr($0, pos + length(ANCHOR))
    sub(/^[[:space:]]+/, "", rest)
    n = split(rest, A, /[[:space:]]+/)

    # Print requested columns (1-based), no newline
    for (k=1; k<=n_idx; k++) {
      printf "%s", SEP
      idx = I[k] + 0
      if (idx >= 1 && idx <= n) printf "%s", A[idx]
      else printf "%s", PH
    }
    found = 1
    exit
  }
  END {
    if (!found) {
      for (k=1; k<=n_idx; k++) printf "%s%s", SEP, PH
    }
  }
' ${file:+"$file"}

exit 0
