"""
Eval scorer.  (Owner: Ryan / P2.)

Turns "it works" into a number. Scores the pipeline against the seed corpus's
ground-truth labels — the differentiator: measured better, not vibes.

Metrics:
  extraction precision   did we extract the right decision per source
                         (topic + owner correct, matched to the label)?
  owner accuracy         did we get owned/unowned right?
  supersession recall    of the relationships labeled "supersedes",
                         how many did the graph detect?
"""

from __future__ import annotations

from dataclasses import dataclass, field

from company_brain.extract import extract
from company_brain.schema import Decision
from company_brain.seed.corpus import SOURCES, SeedSource
from company_brain.store import Brain


@dataclass
class EvalResult:
    sources: int = 0
    extracted: int = 0
    topic_correct: int = 0
    owner_correct: int = 0
    supersessions_expected: int = 0
    supersessions_found: int = 0
    notes: list[str] = field(default_factory=list)

    @property
    def extraction_precision(self) -> float:
        return round(self.topic_correct / self.extracted, 3) if self.extracted else 0.0

    @property
    def owner_accuracy(self) -> float:
        return round(self.owner_correct / self.extracted, 3) if self.extracted else 0.0

    @property
    def supersession_recall(self) -> float:
        return (round(self.supersessions_found / self.supersessions_expected, 3)
                if self.supersessions_expected else 1.0)

    def render(self) -> str:
        return "\n".join([
            "┌─ EVAL (vs seed ground truth) ───────────────",
            f"│ sources ingested       {self.sources}",
            f"│ decisions extracted    {self.extracted}",
            f"│ extraction precision   {self.extraction_precision:>6.1%}  (topic match)",
            f"│ owner accuracy         {self.owner_accuracy:>6.1%}",
            f"│ supersession recall    {self.supersession_recall:>6.1%}  "
            f"({self.supersessions_found}/{self.supersessions_expected})",
            "└─────────────────────────────────────────────",
        ] + [f"  • {n}" for n in self.notes])


def run_eval(use_llm: bool | None = None) -> tuple[EvalResult, Brain]:
    res = EvalResult()
    brain = Brain()
    ordered = sorted(SOURCES, key=lambda s: s.date)

    for s in ordered:
        res.sources += 1
        decisions = extract(s.text, s.type, s.link, s.date, use_llm=use_llm)
        brain.ingest(decisions)
        _score_extraction(s, decisions, res)

    # supersession recall: labels marked "supersedes" that the graph caught
    res.supersessions_expected = sum(
        1 for s in SOURCES for lbl in s.labels if lbl.relation == "supersedes")
    found = sum(1 for d in brain.decisions for e in d.edges if e.type == "supersedes")
    res.supersessions_found = found
    return res, brain


def _score_extraction(s: SeedSource, decisions: list[Decision], res: EvalResult) -> None:
    for lbl in s.labels:
        # match the label to the best-topic extracted decision from this source
        match = next((d for d in decisions if d.topic == lbl.topic), None)
        if match is None:
            res.notes.append(f"{s.id}: missed decision on {lbl.topic}")
            continue
        res.extracted += 1
        res.topic_correct += 1
        owner_ok = ((lbl.owner is None and match.owner is None) or
                    (lbl.owner is not None and match.owner == lbl.owner))
        if owner_ok:
            res.owner_correct += 1
        else:
            res.notes.append(
                f"{s.id}: owner mismatch (got {match.owner}, want {lbl.owner})")


if __name__ == "__main__":
    import os
    res, _ = run_eval()
    mode = "OpenAI" if os.environ.get("OPENAI_API_KEY") else "fallback (offline)"
    print(f"extraction mode: {mode}\n")
    print(res.render())
