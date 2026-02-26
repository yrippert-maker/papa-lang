"""MetaQA HRS Engine — ACM 2025 implementation.

Detects hallucinations via metamorphic prompt mutations.
Works with closed-source models (no token probabilities needed).
"""

import re
from typing import Callable, List

MUTATIONS = [
    lambda q: q,
    lambda q: "Please answer: " + q,
    lambda q: q.replace("?", ". Explain your answer."),
    lambda q: "In one sentence, " + q.lower(),
    lambda q: "Based on verified facts only: " + q,
]


class MetaQAEngine:
    """MetaQA HRS calculation.

    Args:
        llm_call: async callable(prompt: str) -> str
        num_mutations: number of prompt variants to test (3-5)
        similarity_threshold: below this = inconsistency detected
    """

    def __init__(
        self,
        llm_call: Callable[[str], str],
        num_mutations: int = 4,
        similarity_threshold: float = 0.75,
    ):
        self.llm_call = llm_call
        self.num_mutations = num_mutations
        self.similarity_threshold = similarity_threshold

    async def compute_hrs(self, query: str) -> dict:
        """Returns: {hrs, verdict, mutations_used, inconsistency_count, responses}."""
        mutations = MUTATIONS[: self.num_mutations]
        responses = []
        for mutate in mutations:
            mutated_prompt = mutate(query)
            response = await self.llm_call(mutated_prompt)
            responses.append(response)

        inconsistencies = self._count_inconsistencies(responses)
        hrs = inconsistencies / max(len(responses) - 1, 1)
        hrs = min(hrs, 1.0)

        verdict = self._get_verdict(hrs)
        return {
            "hrs": round(hrs, 4),
            "verdict": verdict,
            "mutations_used": len(mutations),
            "inconsistency_count": inconsistencies,
            "responses": responses,
        }

    def _count_inconsistencies(self, responses: List[str]) -> int:
        """Count semantically inconsistent response pairs."""
        if not responses:
            return 0
        baseline = self._normalize(responses[0])
        count = 0
        for resp in responses[1:]:
            similarity = self._jaccard_similarity(baseline, self._normalize(resp))
            if similarity < self.similarity_threshold:
                count += 1
        return count

    def _normalize(self, text: str) -> set:
        words = re.findall(r"\b\w+\b", text.lower())
        stopwords = {"the", "a", "an", "is", "are", "was", "were", "be", "to", "of", "and", "or"}
        return set(w for w in words if w not in stopwords)

    def _jaccard_similarity(self, a: set, b: set) -> float:
        if not a and not b:
            return 1.0
        intersection = len(a & b)
        union = len(a | b)
        return intersection / union if union > 0 else 0.0

    def _get_verdict(self, hrs: float) -> str:
        if hrs < 0.10:
            return "PASS"
        if hrs < 0.20:
            return "WARN"
        return "BLOCK"
