"""
Memory: precedents + corrections.  (Owner: person 4 — Memory + auditor)

THE DIFFERENTIATOR. Almost every team will have multi-agent theater; almost
none will show a measured learning curve. This module is that curve.

Deliberately a plain JSON file, not Letta/Mem0/Zep — those are a multi-hour
integration that demos identically. The preparer reads precedents at run
start and applies them before reasoning from scratch, which is what makes
month 2 better than month 1.

Loop:
    1. preparer runs, gets some residual matches wrong
    2. human corrects a few  -> Correction records
    3. distill()  turns corrections into reusable Precedent rules
    4. next run: preparer loads precedents -> handles those cases itself
"""

from __future__ import annotations

import json
import os

from schemas import Correction, Precedent, dump_list, load_list

STORE = os.path.join(os.path.dirname(__file__), "memory_store.json")


def load() -> tuple[list[Precedent], list[Correction]]:
    if not os.path.exists(STORE):
        return [], []
    with open(STORE) as f:
        data = json.load(f)
    return (load_list(Precedent, data.get("precedents", [])),
            load_list(Correction, data.get("corrections", [])))


def save(precedents: list[Precedent], corrections: list[Correction]) -> None:
    with open(STORE, "w") as f:
        json.dump({"precedents": dump_list(precedents),
                   "corrections": dump_list(corrections)}, f, indent=2)


def precedent_prompt(precedents: list[Precedent]) -> str:
    """Render precedents into text the preparer prepends to its reasoning."""
    if not precedents:
        return "No learned precedents yet. Reason from first principles."
    lines = ["LEARNED PRECEDENTS (apply these before reasoning from scratch):"]
    for p in precedents:
        lines.append(f"- [{p.pattern}] {p.description} -> {p.rule}")
    return "\n".join(lines)


def distill(corrections: list[Correction],
            existing: list[Precedent]) -> list[Precedent]:
    """Turn corrections into precedents.

    STUB: a real version asks an LLM to generalize the correction into a
    reusable rule. Here we map by category keyword so the loop runs offline.
    Person 4: replace the body with an LLM call that reads `was`/`should_be`
    and emits a `pattern` + `rule`.
    """
    known = {p.pattern for p in existing}
    out = list(existing)
    RULES = {
        "fee": ("wire_net_of_fee",
                "bank amount differs from ledger by a small round fee",
                "treat the difference as a bank/wire/processor fee; match gross↔net and book the fee"),
        "invoice": ("one_payment_many_invoices",
                    "one deposit equals the sum of several open invoices",
                    "match one bank line to the N ledger entries whose amounts sum to it"),
        "duplicate": ("ledger_double_book",
                      "ledger has two identical entries for one bank line",
                      "match one; flag the other as a duplicate to reverse"),
        "timing": ("period_cutoff_timing",
                   "ledger date and bank clear date straddle the period end",
                   "match across the cutoff and tag as a timing difference"),
    }
    for c in corrections:
        text = (c.should_be + " " + c.was).lower()
        for kw, (pat, desc, rule) in RULES.items():
            if kw in text and pat not in known:
                out.append(Precedent(
                    id=f"PRE-{len(out)+1:03d}", pattern=pat,
                    description=desc, rule=rule, created_from=[c.id]))
                known.add(pat)
    return out


if __name__ == "__main__":
    p, c = load()
    print(f"loaded {len(p)} precedents, {len(c)} corrections")
    print(precedent_prompt(p))
