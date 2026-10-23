"""Build one member's confidential peer-review PDF from their filled-in copy of template.toml."""

import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
LATEX = HERE.parent / "latex"
PREFIX = "IRS-PM-2026-08-17-ISFT-GRP-16-AnchorAI-Peer-Review"

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


def check(form: dict) -> list[str]:
    errors = [f"{key} is empty" for key in ("reviewer", "student_id") if not form.get(key, "").strip()]
    members = form.get("members", [])
    total = sum(m.get("contribution", 0) for m in members)
    if total != 100:
        errors.append(f"contributions add up to {total}, not 100")
    errors += [
        f"{m['name']}: rating must be 1 to 5" for m in members if m.get("rating") not in range(1, 6)
    ]
    return errors


def document(form: dict) -> str:
    rows = "\n    \\arrayrulecolor{rule}\\midrule\\arrayrulecolor{nusBlue}\n".join(
        f"    {tex(m['name'])} & {m['contribution']} & {m['rating']} & {tex(m.get('comments', ''))} \\\\"
        for m in form["members"]
    )
    notes = tex(form.get("notes", ""))
    notes_block = f"\\minisec{{\\color{{nusBlue}}Notes for the lecturer}}\n{notes}\n" if notes else ""
    return rf"""\documentclass[paper=a4, fontsize=11pt, parskip=half-, headings=small]{{scrreprt}}
\usepackage{{anchorai}}
\graphicspath{{{{{LATEX.as_posix()}/figures/}}}}
\ifoot{{\color{{muted}}Anchor\textcolor{{nusOrange}}{{AI}}\enskip·\enskip Confidential peer review}}
\ohead{{Peer review}}
\begin{{document}}
\section*{{Confidential peer review}}
{{\sffamily Group 16, AnchorAI\par
Reviewer: \textbf{{{tex(form["reviewer"])}}}\enskip·\enskip {tex(form["student_id"])}\par}}
\medskip
Contribution of each member, the reviewer included. Contributions add up to 100\%. Ratings are 1 (poor) to 5 (excellent).
\medskip

{{\small\sffamily\renewcommand{{\arraystretch}}{{1.6}}%
\begin{{tabularx}}{{\linewidth}}{{@{{}}P{{40mm}} c c L@{{}}}}
    \toprule
    \hd{{Member}} & \hd{{Share (\%)}} & \hd{{Rating}} & \hd{{Comments}} \\
    \midrule
{rows}
    \bottomrule
\end{{tabularx}}\par}}
{notes_block}\end{{document}}
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
    job = f"{PREFIX}-{re.sub(r'[^A-Za-z0-9]+', '-', form['reviewer'].strip())}"
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
    print(HERE / f"{job}.pdf")


if __name__ == "__main__":
    main()
