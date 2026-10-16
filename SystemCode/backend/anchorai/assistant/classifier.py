"""Intent detection by embedding similarity to each intent's example centroid, plus the slot rule."""

from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import yaml
from pydantic import BaseModel

from anchorai.assistant.slots import Slots, extract_slots
from anchorai.assistant.tools import name_lookup
from anchorai.config import get_settings

INTENTS_FILE = Path(__file__).parent / "intents.yaml"
UNKNOWN = "unknown"
Encoder = Callable[[list[str]], np.ndarray]


@dataclass(frozen=True)
class IntentSpec:
    name: str
    description: str
    examples: list[str]
    member_slots: tuple[int, int] | None = None


class Prediction(BaseModel):
    intent: str
    score: float
    slots: Slots


def load_intents(path: Path = INTENTS_FILE) -> tuple[list[IntentSpec], float]:
    data = yaml.safe_load(path.read_text())
    specs = [
        IntentSpec(
            name=name,
            description=spec["description"],
            examples=spec["examples"],
            member_slots=tuple(spec["member_slots"]) if "member_slots" in spec else None,
        )
        for name, spec in data["intents"].items()
    ]
    return specs, float(data["threshold"])


class IntentClassifier:
    def __init__(
        self,
        encode: Encoder,
        specs: list[IntentSpec],
        threshold: float,
        instructors: dict[str, str],
        classes: dict[str, str],
    ):
        self.encode, self.specs, self.threshold = encode, specs, threshold
        self.instructors, self.classes = instructors, classes
        rows = []
        for spec in specs:
            emb = encode([self._normalise(t) for t in spec.examples])
            centroid = emb.mean(axis=0)
            rows.append(centroid / np.linalg.norm(centroid))
        self.centroids = np.stack(rows)

    def _normalise(self, text: str) -> str:
        return extract_slots(text, self.instructors, self.classes)[1]

    def classify(self, text: str, context_member_id: str | None = None) -> Prediction:
        slots, normalised = extract_slots(text, self.instructors, self.classes)
        if not slots.member_ids and context_member_id:
            slots.member_ids = [context_member_id]
        sims = self.centroids @ self.encode([normalised])[0]
        # Slot rule: an intent whose member-id requirement isn't met can't be the answer.
        n = len(slots.member_ids)
        for i, spec in enumerate(self.specs):
            if spec.member_slots and not spec.member_slots[0] <= n <= spec.member_slots[1]:
                sims[i] = -1.0
        best = int(sims.argmax())
        score = float(sims[best])
        intent = self.specs[best].name if score >= self.threshold else UNKNOWN
        return Prediction(intent=intent, score=round(score, 4), slots=slots)


def sentence_encoder(model_name: str) -> Encoder:
    # Imported here: it loads torch (seconds), which the API and tests shouldn't pay unless used.
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name)
    return lambda texts: model.encode(texts, normalize_embeddings=True)


@lru_cache
def get_classifier() -> IntentClassifier:
    specs, threshold = load_intents()
    instructors, classes = name_lookup()
    encode = sentence_encoder(get_settings().assistant_embedding_model)
    return IntentClassifier(encode, specs, threshold, instructors, classes)
