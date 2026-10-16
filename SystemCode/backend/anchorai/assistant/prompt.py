"""The grounded prompt from notebooks/c_llm_smoke.ipynb: the LLM only rewrites evidence."""

from anchorai.assistant.tools import Evidence

DONT_KNOW = "I don't know based on the data I have."

SYSTEM = f"""You are AnchorAI's assistant for gym staff.
Answer ONLY from the evidence lines you are given. Each line starts with an id such as [E1].
After each sentence, cite the ids it is based on, e.g. [E1][E3].
If the evidence does not answer the question, reply exactly: {DONT_KNOW}
Never invent numbers, names, offers or reasons that are not in the evidence.
Use plain English, at most 80 words, no tables or headings."""


def evidence_block(evidence: list[Evidence]) -> str:
    return "\n".join(f"[{e.id}] {e.text}" for e in evidence) or "(no evidence)"


def build_messages(question: str, evidence: list[Evidence]) -> list[dict]:
    return [
        {"role": "system", "content": SYSTEM},
        {
            "role": "user",
            "content": f"Question: {question}\n\nEvidence:\n{evidence_block(evidence)}",
        },
    ]
