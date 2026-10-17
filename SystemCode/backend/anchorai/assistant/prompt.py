"""The grounded prompt from notebooks/c_llm_smoke.ipynb: the LLM only rewrites evidence."""

import re
from collections.abc import Sequence

from anchorai.assistant.tools import Evidence

DONT_KNOW = "I don't know based on the data I have."

SYSTEM = f"""You are AnchorAI's assistant for gym staff, in a chat.
Earlier messages only tell you what the user is referring to ("they", "that offer").
Answer ONLY from the evidence lines in the latest message. Each line starts with an id such as [E1].
End every sentence and bullet, including the first, with the ids it is based on, e.g. [E1][E3].
If the evidence does not answer the question, reply exactly: {DONT_KNOW}
Never invent numbers, names, offers or reasons that are not in the evidence.
Do not add advice, an order to act in, or remarks about what the evidence does or does not show, unless an evidence line says it.
Use plain English, at most 80 words (a list of members may take one bullet each). A short "- " bullet list is fine for several items.
No tables or headings."""
HISTORY_TURNS = 3
# Old answers cite evidence ids that the latest message reuses for different lines.
CITATIONS = re.compile(r"\s*(\[E\d+\])+")


def evidence_block(evidence: list[Evidence]) -> str:
    return "\n".join(f"[{e.id}] {e.text}" for e in evidence) or "(no evidence)"


def build_messages(
    question: str, evidence: list[Evidence], history: Sequence[tuple[str, str]] = ()
) -> list[dict]:
    """`history` is earlier (question, answer) pairs, oldest first."""
    earlier = []
    for asked, answered in history[-HISTORY_TURNS:]:
        earlier += [
            {"role": "user", "content": asked},
            {"role": "assistant", "content": CITATIONS.sub("", answered)},
        ]
    return [
        {"role": "system", "content": SYSTEM},
        *earlier,
        {
            "role": "user",
            "content": f"Question: {question}\n\nEvidence:\n{evidence_block(evidence)}",
        },
    ]
