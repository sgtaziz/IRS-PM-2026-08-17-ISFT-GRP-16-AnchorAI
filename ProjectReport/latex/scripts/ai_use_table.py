"""Turn docs/AI_USE.md into the rows of the report's AI-use appendix (appendices/f-ai-use-rows.tex)."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SPECIAL = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}


LABELS = {"Stream A": "Member intelligence", "Stream B": "Decision and optimisation", "Stream C": "Knowledge and interaction"}


def tex(text: str) -> str:
    for old, new in LABELS.items():
        text = text.replace(old, new)
    parts = re.split(r"`([^`]*)`", text)
    out = []
    for i, part in enumerate(parts):
        if i % 2:
            out.append(r"\code{" + part.replace("{", "").replace("}", "") + "}")
        else:
            out.append("".join(SPECIAL.get(c, c) for c in part))
    return "".join(out).replace("–", "--")


rows = []
for line in (ROOT / "docs/AI_USE.md").read_text().splitlines():
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    if len(cells) == 5 and re.match(r"\d{4}-\d{2}-\d{2}", cells[0]):
        date, member, tool, used, changed = cells
        rows.append(f"{date[5:]} & {tex(member)} & {tex(used)} & {tex(changed)} \\\\")
out = Path(__file__).resolve().parent.parent / "appendices" / "f-ai-use-rows.tex"
out.write_text("\n".join(rows) + "\n")
print(len(rows), "rows ->", out)
