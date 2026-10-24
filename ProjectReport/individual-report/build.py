"""Build one member's individual project report PDF from their filled-in copy of template.toml."""

import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
LATEX = HERE.parent / "latex"
PREFIX = "IRS-PM-2026-08-17-ISFT-GRP-16-AnchorAI-Individual-Report"
GROUP = "16"
TITLE = "AnchorAI: explainable, budget-aware retention planning for gyms"
LIMIT = 150

SPECIAL = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def tex(text: str) -> str:
    text = "".join(SPECIAL.get(c, c) for c in text.strip())
    return re.sub(r"\n\s*\n", r"\\par ", text)


def words(text: str) -> int:
    return len(text.split())


def check(form: dict) -> list[str]:
    keys = ("name", "student_id", "email", "contributions", "reflections", "ai_declaration")
    errors = [f"{key} is empty" for key in keys if not form.get(key, "").strip()]
    errors += [
        f"{key} has {words(form[key])} words, the limit is {LIMIT}"
        for key in ("contributions", "reflections")
        if words(form.get(key, "")) > LIMIT
    ]
    return errors


def document(form: dict) -> str:
    fields = [
        ("Student name", tex(form["name"])),
        ("Matriculation no.", tex(form["student_id"])),
        ("NUS email", tex(form["email"])),
        ("Group number", GROUP),
        ("Project title", tex(TITLE)),
    ]
    rows = "\n".join(f"    \\hd{{{label}}} & {value} \\\\" for label, value in fields)
    return rf"""\documentclass[paper=a4, fontsize=11pt, parskip=half-, headings=small]{{scrreprt}}
\usepackage{{anchorai}}
\graphicspath{{{{{LATEX.as_posix()}/figures/}}}}
\ifoot{{\color{{muted}}Anchor\textcolor{{brandBlue}}{{AI}}\enskip·\enskip Group {GROUP} individual project report}}
\ohead{{Individual project report}}
\begin{{document}}
\section*{{Individual project report}}
{{\sffamily\renewcommand{{\arraystretch}}{{1.4}}%
\begin{{tabularx}}{{\linewidth}}{{@{{}}p{{40mm}} L@{{}}}}
{rows}
\end{{tabularx}}\par}}
\minisec{{\color{{nusBlue}}My contributions to the project}}
{tex(form["contributions"])}
\minisec{{\color{{nusBlue}}Self-reflections}}
{tex(form["reflections"])}
\minisec{{\color{{nusBlue}}Use of AI tools}}
{tex(form["ai_declaration"])}
\end{{document}}
"""


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: build.py <your-name>.toml")
    source = Path(sys.argv[1]).resolve()
    form = tomllib.loads(source.read_text())
    if errors := check(form):
        sys.exit("Fix these first:\n  " + "\n  ".join(errors))
    build = HERE / "build"
    build.mkdir(exist_ok=True)
    job = f"{PREFIX}-{re.sub(r'[^A-Za-z0-9]+', '-', form['name'].strip())}"
    (build / f"{job}.tex").write_text(document(form))
    env = {**os.environ, "TEXINPUTS": f"{LATEX}:"}
    for _ in range(2):
        run = subprocess.run(
            ["lualatex", "-interaction=nonstopmode", "-halt-on-error", f"{job}.tex"],
            cwd=build,
            env=env,
            capture_output=True,
            text=True,
        )
        if run.returncode:
            sys.exit(f"LaTeX failed; see {build / job}.log")
    shutil.copy(build / f"{job}.pdf", HERE / f"{job}.pdf")
    print(f"{HERE / job}.pdf  (contributions {words(form['contributions'])}, reflections {words(form['reflections'])} words)")


if __name__ == "__main__":
    main()
