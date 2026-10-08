#!/usr/bin/env bash
set -e
dir="$(cd -- "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd -P)"

cd "$1" || exit 1
trap 'rm -f main.{tex,aux,log,out,pdf}' EXIT
shopt -s nullglob
{
    cat <<'EOF'
\documentclass{article}
\usepackage[margin=0pt]{geometry}
\pagestyle{empty}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{graphicx}
\usepackage{siunitx}
\usepackage{multirow}
\usepackage[table]{xcolor}
\newcommand{\bft}{\bfseries}
\usepackage{xspace}
\providecommand{\toolnameformat}[1]{\textsc{#1}\xspace}
\providecommand{\caketaiger}{\toolnameformat{Caketaiger}}
\providecommand{\certifaiger}{\toolnameformat{Certifaiger}}
\begin{document}
EOF
    for f in *.tex; do
        [[ "$f" == "main.tex" ]] && continue
        printf '\\input{%s} \n\\vspace{1cm}\n\n' $f
    done
    for f in *.pdf; do
        [[ "$f" == "main.pdf" ]] && continue
        printf '\\includegraphics[width=.95\\paperwidth]{%s} \n\n' $f
    done
    printf '\\end{document}\n'
} >main.tex

if command -v pdflatex >/dev/null 2>&1; then
    pdflatex -halt-on-error -interaction=nonstopmode main.tex >/dev/null 2>&1
    if grep -q 'Table widths have changed' main.log; then
        pdflatex -halt-on-error -interaction=nonstopmode main.tex >/dev/null 2>&1
    fi
elif [ -f "$dir"/tectonic ]; then
	if curl --silent --max-time 2 http://1.1.1.1 >/dev/null; then
		"$dir"/tectonic main.tex
	else
		"$dir"/tectonic --only-cached main.tex		
	fi
else
    echo "No LaTeX compiler found" >&2
    exit 1
fi

mv main.pdf "../$(basename "$PWD").pdf"
printf '%s\n' "Produced ${PWD}.pdf"
