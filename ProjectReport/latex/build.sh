#!/bin/sh
# Full build: LuaLaTeX, biber, two more passes. Fails fast on a LaTeX error.
# Usage: ./build.sh [main|main-short]
set -e
cd "$(dirname "$0")"
job="${1:-main}"
mkdir -p build
run() { lualatex -interaction=nonstopmode -halt-on-error -file-line-error -output-directory=build "$job.tex" > "build/$job-run.txt" 2>&1 || { grep -E "^\./.*:[0-9]+:|^!" "build/$job.log" | head -5; exit 1; }; }
run
biber --quiet "build/$job" > /dev/null
run
run
grep -E "Overfull|Undefined|undefined|Missing character" "build/$job.log" | sort | uniq -c || true
pdfinfo "build/$job.pdf" | grep Pages
