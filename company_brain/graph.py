"""
Edge/conflict detection + attention rules.  (Owner: Ryan / P2.)

Pure functions over `Decision` sets. `relate()` decides how a new decision
relates to what's already live; `compute_attention()` derives the attention
queue from the final graph state.

Supersession vs conflict — the distinction the whole demo turns on:

    a newer decision that ANNOUNCES it replaces something   -> supersedes
    a decision that just asserts a RIVAL VALUE for the same
      thing, while the old one is still live                -> conflicts

Time alone can't tell those apart. "We're changing the free tier — 50/day
going forward" replaces the old number and says so. "Sales is quoting Pro at
$59" does not: both records are live, both are being followed, and that is
the thing nobody notices until it costs something. So supersession is driven
by an explicit cue, and conflict by two live statements whose subject matches
but whose value does not.

Every edge carries a `rationale`, because on stage the second question is
always "why does it think that?".

The attention rules live in `rules.json` — severity, message and suggested
action are DATA (AGENTS.md §5: "attention rules are data, not hardcoded UI").
Adding a rule is one JSON entry plus one predicate below; the UI ships nothing.
"""

from __future__ import annotations

import json
import os
import re

from company_brain.schema import Decision, Edge

RULES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rules.json")

# Tuned against company_brain/eval.py — not by vibes. `conflict` is the bar for
# "these two are about the same thing"; below `related` they are unrelated.
THRESHOLDS = {"conflict": 0.40, "related": 0.22}

_SUPERSEDE_SIGNALS = ("supersede", "changing", "going forward", "instead of",
                      "no longer", "replace", "update", "now ", "revised")
_STOP = {"the", "our", "and", "for", "with", "that", "this", "stay", "around",
         "current", "levels", "costs", "cost", "about", "into", "from", "will",
         "each", "they", "them", "these", "those", "their", "over", "under",
         # interrogatives + auxiliaries: these carry no topic meaning, but a
         # question is mostly made of them, so leaving them in lets a query
         # "match" a decision on the word "what" alone.
         "what", "who", "whom", "when", "where", "why", "how", "does", "did",
         "are", "was", "were", "can", "could", "should", "would", "have",
         "has", "had", "you", "your", "any", "not", "but", "its"}


def _supersede_signal(text: str) -> str | None:
    """The cue itself, not just a bool — it goes into the rationale."""
    low = text.lower()
    return next((sig for sig in _SUPERSEDE_SIGNALS if sig in low), None)


def keywords(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9][a-z0-9+/.-]{2,}", text.lower())
    return {w for w in words if w not in _STOP}


# ---------------------------------------------------------------------------
# similarity — deliberately lexical: explainable, instant, no key required
# ---------------------------------------------------------------------------

def similarity(a: str, b: str) -> float:
    ka, kb = keywords(a), keywords(b)
    if not ka or not kb:
        return 0.0
    return len(ka & kb) / len(ka | kb)


def _rival_values(a: str, b: str) -> tuple[set[str], set[str]]:
    """What each statement says that the other doesn't — '49/month' vs
    '59/month'. Both sides non-empty is what makes it a rivalry rather than
    one statement simply being longer than the other."""
    ka, kb = keywords(a), keywords(b)
    return ka - kb, kb - ka


def _is_rival_value(mine: set[str], theirs: set[str]) -> bool:
    """A conflict is two live decisions naming a DIFFERENT NUMBER for the same
    thing: $49/month vs $59/month, 100 calls/day vs 50, 30 days vs 90.

    The numeric requirement is doing real work. Text similarity alone cannot
    tell "Adopt the billing service" from "Sunset the billing service" — one
    token apart, exactly like the pricing pair — and treating every verb swap
    as a contradiction buried the attention queue in 81 items on the generated
    corpus. A changed value is the conflict that actually costs a company
    something, and it is the one we can assert honestly. A rival that is NOT
    numeric (one vendor swapped for another) almost always arrives with a
    supersession cue, and rules 1 and 3 below pick it up there."""
    if not mine or not theirs:
        return False
    has_digit = lambda ws: any(any(c.isdigit() for c in w) for w in ws)
    return has_digit(mine) and has_digit(theirs)


def _short(s: str, n: int = 52) -> str:
    return s if len(s) <= n else s[:n].rstrip() + "…"


def _phrase(words: set[str], statement: str, limit: int = 3) -> str:
    """Render tokens in the order they appear, so a rationale reads like
    language rather than a set dump."""
    out: list[str] = []
    for raw in re.findall(r"[A-Za-z0-9$][A-Za-z0-9$+/.,%-]*", statement or ""):
        w = raw.strip(".,").lower()
        if w in words and w not in out:
            out.append(w)
    out.extend(sorted(w for w in words if w not in out))
    return ", ".join(out[:limit])


# ---------------------------------------------------------------------------
# relate
# ---------------------------------------------------------------------------

def relate(new: Decision, decisions: list[Decision]) -> None:
    """Mutate `new` (and its peers) to record edges/status on ingest.

    A superseded decision is NOT deleted — it drops to needs_review so the
    attention queue can surface "check it still holds". Two conflicting
    decisions both stay live: that is the point, and both ends get the edge
    so either one opens onto the other in the UI.
    """
    peers = [d for d in decisions
             if d.id != new.id and d.status == "live"
             and (d.topic == new.topic
                  or similarity(new.statement, d.statement) >= THRESHOLDS["related"])]

    for p in peers:
        sim = similarity(new.statement, p.statement)
        shared = _phrase(keywords(new.statement) & keywords(p.statement), p.statement)
        newer = new.decided_on > p.decided_on
        cue = _supersede_signal(new.statement)

        same_ground = p.topic == new.topic or sim >= THRESHOLDS["conflict"]

        # 1. it says it is replacing something
        if cue and same_ground and new.decided_on >= p.decided_on:
            new.edges.append(Edge(
                type="supersedes", target_id=p.id, confidence=0.9,
                rationale=(f"{new.id} says “{cue.strip()}” and covers the same ground "
                           f"as {p.id} ({shared}).")))
            p.status = "needs_review"
            continue

        # 2. a rival value for the same thing, and nobody claimed to replace
        mine, theirs = _rival_values(new.statement, p.statement)
        if sim >= THRESHOLDS["conflict"] and _is_rival_value(mine, theirs):
            why = (f"Both live and both about {shared}; {p.id} says "
                   f"{_phrase(theirs, p.statement, 2)} while {new.id} says "
                   f"{_phrase(mine, new.statement, 2)}.")
            conf = round(min(0.95, 0.5 + sim * 0.6), 2)
            new.edges.append(Edge(type="conflicts", target_id=p.id,
                                  confidence=conf, rationale=why))
            p.edges.append(Edge(type="conflicts", target_id=new.id,
                                confidence=conf, rationale=why))
            continue

        # 3. same topic, later date, no rival value: a time-ordered replacement
        if newer and p.topic == new.topic:
            new.edges.append(Edge(
                type="supersedes", target_id=p.id, confidence=0.6,
                rationale=(f"{new.id} ({new.decided_on}) is the later decision on "
                           f"{new.topic}; {p.id} is from {p.decided_on}.")))
            p.status = "needs_review"
            continue

        # 4. same day, same topic — two calls made in parallel
        if new.decided_on == p.decided_on and p.topic == new.topic:
            why = f"{new.id} and {p.id} were both decided on {new.decided_on} about {new.topic}."
            new.edges.append(Edge(type="conflicts", target_id=p.id,
                                  confidence=0.7, rationale=why))
            p.edges.append(Edge(type="conflicts", target_id=new.id,
                                confidence=0.7, rationale=why))


# ---------------------------------------------------------------------------
# attention — rules in rules.json, predicates here
# ---------------------------------------------------------------------------

_rules_cache: list[dict] | None = None


def rules() -> list[dict]:
    global _rules_cache
    if _rules_cache is None:
        with open(RULES_PATH, encoding="utf-8") as f:
            _rules_cache = sorted(json.load(f), key=lambda r: r["severity"])
    return _rules_cache


def _ctx(decisions: list[Decision]) -> dict:
    superseded_by: dict[str, tuple[str, str]] = {}
    for d in decisions:
        for e in d.edges:
            if e.type == "supersedes":
                superseded_by[e.target_id] = (d.id, e.rationale)
    changed: set[str] = set()          # terms whose fact has moved
    for d in decisions:
        if d.status in ("needs_review", "superseded"):
            changed |= keywords(d.statement)
    return {"decisions": decisions, "by_id": {d.id: d for d in decisions},
            "superseded_by": superseded_by, "changed": changed}


def _unowned(ctx) -> list[dict]:
    return [{"decision_id": d.id, "related_id": None, "statement": _short(d.statement)}
            for d in ctx["decisions"] if d.owner is None and d.status != "superseded"]


def _superseded_unedited(ctx) -> list[dict]:
    out = []
    for d in ctx["decisions"]:
        if d.status == "needs_review" and d.id in ctx["superseded_by"]:
            newer_id, why = ctx["superseded_by"][d.id]
            newer = ctx["by_id"].get(newer_id)
            out.append({"decision_id": d.id, "related_id": newer_id,
                        "other": newer_id, "rationale": why,
                        "statement": _short(d.statement),
                        "other_statement": _short(newer.statement, 40) if newer else newer_id})
    return out


def _drifted_assumption(ctx) -> list[dict]:
    out = []
    for d in ctx["decisions"]:
        if d.status != "live":
            continue
        for a in d.assumptions:
            hit = keywords(a) & ctx["changed"]
            if hit:
                out.append({"decision_id": d.id, "related_id": None,
                            "statement": _short(d.statement),
                            "moved": ", ".join(sorted(hit))})
                break
    return out


def _live_overlap(ctx) -> list[dict]:
    """Two live decisions that cover the same ground — either because
    relate() drew a conflicts edge, or because they simply share a topic."""
    out, seen = [], set()
    live = [d for d in ctx["decisions"] if d.status == "live"]
    for d in live:
        for e in d.edges:
            other = ctx["by_id"].get(e.target_id)
            if e.type != "conflicts" or other is None or other.status != "live":
                continue
            pair = frozenset((d.id, other.id))
            if pair in seen:
                continue
            seen.add(pair)
            out.append({"decision_id": d.id, "related_id": other.id,
                        "other": other.id, "rationale": e.rationale,
                        "statement": _short(d.statement),
                        "other_statement": _short(other.statement, 40),
                        "detail": _rival_detail(d.statement, other.statement)})
    for i, a in enumerate(live):
        for b in live[i + 1:]:
            pair = frozenset((a.id, b.id))
            if a.topic == b.topic and pair not in seen:
                seen.add(pair)
                out.append({"decision_id": a.id, "related_id": b.id, "other": b.id,
                            "rationale": f"Both are live on {a.topic}.",
                            "statement": _short(a.statement),
                            "other_statement": _short(b.statement, 40),
                            "detail": f"both live on {a.topic}"})
    return out


def _rival_detail(a: str, b: str) -> str:
    """The short form of the disagreement — "49/month vs 59/month". The full
    sentence lives on the edge's rationale; the attention panel gets the part
    a judge can read at a glance."""
    mine, theirs = _rival_values(a, b)
    if not mine or not theirs:
        return "same ground"
    return f"{_phrase(mine, a, 1)} vs {_phrase(theirs, b, 1)}"


PREDICATES = {
    "unowned": _unowned,
    "superseded_unedited": _superseded_unedited,
    "drifted_assumption": _drifted_assumption,
    "live_overlap": _live_overlap,
}


def compute_attention(decisions: list[Decision]) -> list[dict]:
    """Derive the attention queue from final graph state.

    Keys `type`, `decision_id`, `message` and `related_id` are the UI's
    contract and don't change; `rule_id`, `severity`, `title` and `action`
    are additions the UI can pick up when it wants them.
    """
    ctx = _ctx(decisions)
    items: list[dict] = []
    for rule in rules():
        predicate = PREDICATES.get(rule["id"])
        if predicate is None:
            continue
        for fields in predicate(ctx):
            try:
                message = rule["message"].format(**fields).strip()
            except (KeyError, IndexError):
                message = rule["title"]
            items.append({
                "type": rule["type"], "rule_id": rule["id"],
                "severity": rule["severity"], "title": rule["title"],
                "decision_id": fields["decision_id"],
                "related_id": fields.get("related_id"),
                "message": message, "action": rule.get("action", {}),
            })
    items.sort(key=lambda i: (i["severity"], i["decision_id"]))
    return items
