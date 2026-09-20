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
  conflict recall        of the relationships labeled "conflicts", how many
                         did the graph detect? This is the one the demo turns
                         on: a rival live decision that nobody reconciled.
  false edges            relationships the graph asserted that ground truth
                         does not have. Reported on its own line because a
                         confidently WRONG edge costs more than a missed one —
                         the whole product is a claim about knowing what
                         contradicts what.
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
    conflicts_expected: int = 0
    conflicts_found: int = 0
    false_edges: int = 0
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

    @property
    def conflict_recall(self) -> float:
        return (round(self.conflicts_found / self.conflicts_expected, 3)
                if self.conflicts_expected else 1.0)

    def render(self) -> str:
        return "\n".join([
            "┌─ EVAL (vs seed ground truth) ───────────────",
            f"│ sources ingested       {self.sources}",
            f"│ decisions extracted    {self.extracted}",
            f"│ extraction precision   {self.extraction_precision:>6.1%}  (topic match)",
            f"│ owner accuracy         {self.owner_accuracy:>6.1%}",
            f"│ supersession recall    {self.supersession_recall:>6.1%}  "
            f"({self.supersessions_found}/{self.supersessions_expected})",
            f"│ conflict recall        {self.conflict_recall:>6.1%}  "
            f"({self.conflicts_found}/{self.conflicts_expected})",
            f"│ false edges            {self.false_edges:>6}  "
            f"(asserted, not in ground truth)",
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

    _score_relations(brain, res)
    return res, brain


def _score_relations(brain: Brain, res: EvalResult) -> None:
    """Grade the edges the graph derived against the labeled relations.

    A label says "the decision from this source supersedes / conflicts with an
    earlier one on the same topic", so an edge is credited when its newer end
    sits on a topic that was labeled with that relation. Anything else the
    graph asserted is a false edge.
    """
    expected: set[tuple[str, str]] = set()
    for s in SOURCES:
        for lbl in s.labels:
            if lbl.relation != "none":
                expected.add((lbl.topic, lbl.relation))
    res.supersessions_expected = sum(
        1 for s in SOURCES for lbl in s.labels if lbl.relation == "supersedes")
    res.conflicts_expected = sum(
        1 for s in SOURCES for lbl in s.labels if lbl.relation == "conflicts")

    by_id = {d.id: d for d in brain.decisions}
    seen: set[frozenset] = set()
    hit_topics: set[tuple[str, str]] = set()

    for d in brain.decisions:
        for e in d.edges:
            other = by_id.get(e.target_id)
            if other is None:
                continue
            pair = frozenset((d.id, other.id))
            if (pair, e.type) in seen:      # conflicts are recorded on both ends
                continue
            seen.add((pair, e.type))
            newer = d if d.decided_on >= other.decided_on else other
            key = (newer.topic, e.type)
            if key in expected:
                hit_topics.add(key)
                if e.type == "supersedes":
                    res.supersessions_found += 1
                elif e.type == "conflicts":
                    res.conflicts_found += 1
            else:
                res.false_edges += 1
                res.notes.append(
                    f"false edge: {d.id} {e.type} {other.id} ({newer.topic})")

    for topic, relation in sorted(expected - hit_topics):
        res.notes.append(f"missed {relation} on {topic}")


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
    import sys

    # Same Windows-console UTF-8 guard as run_demo.py (see there for why).
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    res, _ = run_eval()
    mode = "OpenAI" if os.environ.get("OPENAI_API_KEY") else "fallback (offline)"
    print(f"extraction mode: {mode}\n")
    print(res.render())
