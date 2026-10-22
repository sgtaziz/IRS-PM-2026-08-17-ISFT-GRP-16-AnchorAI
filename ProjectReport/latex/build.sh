#!/bin/sh
# Full build: LuaLaTeX, biber, two more passes. Fails fast on a LaTeX error.
set -e
cd "$(dirname "$0")"
mkdir -p build
run() { lualatex -interaction=nonstopmode -halt-on-error -file-line-error -output-directory=build main.tex > build/run.txt 2>&1 || { grep -E "^\./.*:[0-9]+:|^!" build/main.log | head -5; exit 1; }; }
run
biber --quiet build/main > /dev/null
run
run
grep -E "Overfull|Undefined|undefined|Missing character" build/main.log | sort | uniq -c || true
pdfinfo build/main.pdf | grep Pages
