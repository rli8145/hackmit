"""
The data contract.  (AGENTS.md §5 — the only shared surface across P1/P2/P3.)

Everything speaks `Decision`. The pipeline PRODUCES them, the store/graph
RELATE them, the UI CONSUMES them, the eval GRADES against labeled ones.
Change this shape only by agreement.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Literal

Status = Literal["live", "superseded", "needs_review"]
EdgeType = Literal["depends_on", "supersedes", "conflicts"]
SourceType = Literal["slack", "fellow", "notion", "paste", "audio"]


@dataclass
class Source:
    type: str            # SourceType
    link: str            # deep-link back to where it was said


@dataclass
class Evidence:
    verbatim_quote: str  # exact text from the source — never paraphrased
    link: str


@dataclass
class Edge:
    type: str            # EdgeType
    target_id: str
    # Why the graph believes this. An edge without a reason is a claim; with
    # one it is evidence, and "why do those two conflict?" has an answer on
    # stage. Defaulted so every existing Edge(type=, target_id=) still works.
    confidence: float = 1.0
    rationale: str = ""


@dataclass
class Decision:
    id: str
    statement: str                       # the decision, one sentence
    status: str = "live"                 # Status
    owner: str | None = None             # None -> unowned (attention trigger)
    decided_on: str = ""                 # ISO date
    source: Source | None = None
    evidence: list[Evidence] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    # free-form topic tag used for overlap/conflict grouping; the pipeline sets it
    topic: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Decision":
        d = dict(d)
        src = d.get("source")
        d["source"] = Source(**src) if isinstance(src, dict) else src
        d["evidence"] = [Evidence(**e) if isinstance(e, dict) else e
                         for e in d.get("evidence", [])]
        d["edges"] = [Edge(**e) if isinstance(e, dict) else e
                      for e in d.get("edges", [])]
        return cls(**d)


# ---------------------------------------------------------------------------
# Ground truth for eval (seed corpus only) — never surfaced in the product.
# ---------------------------------------------------------------------------

@dataclass
class LabeledDecision:
    """What SHOULD be extracted from a seed source, for scoring."""
    statement_gist: str          # canonical meaning (matched loosely)
    topic: str
    owner: str | None
    should_be_unowned: bool
    # ground-truth relationship to an earlier decision on the same topic
    relation: str = "none"       # "none" | "supersedes" | "conflicts"


def dump(decisions: list[Decision]) -> list[dict]:
    return [d.to_dict() for d in decisions]


def load(rows: list[dict]) -> list[Decision]:
    return [Decision.from_dict(r) for r in rows]
