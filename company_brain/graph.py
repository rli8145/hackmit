"""
Edge/conflict detection + attention rules.  (Owner: Ryan / P2.)

Pure functions over `Decision` sets. `relate()` decides how a new decision
relates to what's already live (supersedes vs conflicts). `compute_attention()`
derives the attention queue from the final graph state — the four triggers from
AGENTS.md §3, expressed as data, not hardcoded UI.
"""

from __future__ import annotations

import re

from company_brain.schema import Decision, Edge

_SUPERSEDE_SIGNALS = ("supersede", "changing", "going forward", "instead of",
                      "no longer", "replace", "update", "now ", "revised")
_STOP = {"the", "our", "and", "for", "with", "that", "this", "stay", "around",
         "current", "levels", "costs", "cost", "about", "into", "from", "will",
         "each", "they", "them", "these", "those", "their", "over", "under"}


def _supersede_signal(text: str) -> bool:
    low = text.lower()
    return any(sig in low for sig in _SUPERSEDE_SIGNALS)


def keywords(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9][a-z0-9+/.-]{2,}", text.lower())
    return {w for w in words if w not in _STOP}


def relate(new: Decision, decisions: list[Decision]) -> None:
    """Mutate `new` (and its peers) to record edges/status on ingest.

    A newer decision on the same topic supersedes the live one it replaces
    (the old one is NOT deleted — it drops to needs_review so the attention
    queue can surface "check it still holds"). Same-date rivals conflict.
    """
    live_peers = [d for d in decisions
                  if d.topic == new.topic and d.id != new.id and d.status == "live"]
    for p in live_peers:
        if new.decided_on > p.decided_on or _supersede_signal(new.statement):
            new.edges.append(Edge(type="supersedes", target_id=p.id))
            p.status = "needs_review"
        elif new.decided_on == p.decided_on:
            new.edges.append(Edge(type="conflicts", target_id=p.id))
            p.edges.append(Edge(type="conflicts", target_id=new.id))


def compute_attention(decisions: list[Decision]) -> list[dict]:
    """Derive the attention queue from final graph state."""
    by_id = {d.id: d for d in decisions}
    items: list[dict] = []

    # who supersedes whom (reverse lookup)
    superseded_by: dict[str, str] = {}
    for d in decisions:
        for e in d.edges:
            if e.type == "supersedes":
                superseded_by[e.target_id] = d.id

    changed_keywords: set[str] = set()  # terms whose fact has moved
    for d in decisions:
        if d.status in ("needs_review", "superseded"):
            changed_keywords |= keywords(d.statement)

    for d in decisions:
        # 1. unowned
        if d.owner is None and d.status != "superseded":
            items.append({"type": "unowned", "decision_id": d.id,
                          "message": "Nobody is accountable — assign an owner.",
                          "related_id": None})
        # 2. superseded-but-unedited
        if d.status == "needs_review" and d.id in superseded_by:
            newer = superseded_by[d.id]
            items.append({"type": "superseded", "decision_id": d.id,
                          "message": f"A newer decision ({newer}) changed this; "
                                     f"it still reads as-is — check it still holds.",
                          "related_id": newer})
        # 3. assumption drift
        for a in d.assumptions:
            hit = keywords(a) & changed_keywords
            if hit and d.status == "live":
                items.append({"type": "assumption_drift", "decision_id": d.id,
                              "message": f"An assumption underneath this has moved "
                                         f"({', '.join(sorted(hit))}) — re-verify.",
                              "related_id": None})
                break

    # 4. overlap: two LIVE decisions on the same topic
    seen: set[tuple] = set()
    live = [d for d in decisions if d.status == "live"]
    for i, a in enumerate(live):
        for b in live[i + 1:]:
            if a.topic == b.topic and (a.id, b.id) not in seen:
                seen.add((a.id, b.id))
                items.append({"type": "overlap", "decision_id": a.id,
                              "message": f"Two live decisions cover the same ground "
                                         f"as {b.id} — reconcile the record.",
                              "related_id": b.id})
    return items
