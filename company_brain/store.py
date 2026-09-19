"""
Store + the Brain.  (Owner: Ryan / P2.)

Holds decisions, ingests new ones (running edge/conflict detection), answers
queries, and renders the graph + attention queue for the UI.

Backend: in-memory + lexical similarity by default so everything runs with no
dependencies. Elasticsearch is the intended production store (Elastic track) —
swap `search()` to an ES query; the rest of the interface is unchanged. If ES
setup fights you, this in-memory backend IS the fallback (AGENTS.md §7).
"""

from __future__ import annotations

import difflib

from company_brain.graph import compute_attention, keywords, relate
from company_brain.schema import Decision


class Brain:
    def __init__(self) -> None:
        self.decisions: list[Decision] = []

    # -- ingest -------------------------------------------------------------
    def ingest(self, new: list[Decision]) -> None:
        for d in new:
            relate(d, self.decisions)     # detect edges/status vs current set
            self.decisions.append(d)

    # -- read ---------------------------------------------------------------
    def get(self, decision_id: str) -> Decision | None:
        return next((d for d in self.decisions if d.id == decision_id), None)

    def attention(self) -> list[dict]:
        return compute_attention(self.decisions)

    def graph(self) -> dict:
        return {
            "nodes": [{"id": d.id, "statement": d.statement, "status": d.status,
                       "owner": d.owner, "topic": d.topic} for d in self.decisions],
            "edges": [{"source": d.id, "type": e.type, "target": e.target_id}
                      for d in self.decisions for e in d.edges],
        }

    def search(self, query: str, k: int = 5) -> list[tuple[Decision, float]]:
        """Lexical similarity search. Swap body for an Elasticsearch query to
        satisfy the Elastic track; keyword+semantic over statement + evidence."""
        qk = keywords(query)
        # prefer current state: a live decision outranks the one it superseded
        status_boost = {"live": 0.12, "needs_review": 0.0, "superseded": -0.12}
        scored = []
        for d in self.decisions:
            hay = d.statement + " " + " ".join(e.verbatim_quote for e in d.evidence)
            lex = difflib.SequenceMatcher(None, query.lower(), hay.lower()).ratio()
            overlap = len(qk & keywords(hay)) / (len(qk) or 1)
            score = 0.5 * lex + 0.5 * overlap + status_boost.get(d.status, 0.0)
            scored.append((d, round(score, 3)))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]
