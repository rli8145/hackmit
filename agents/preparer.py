"""
Preparer agent.  (Owner: person 2 — Preparer + pre-matcher)

Works the messy residual the pre-matcher couldn't clear. Reads learned
precedents first, applies them, escalates anything it can't defend.

TWO MODES:
  - LLM mode (the real thing): Claude reasons over the residual with tools.
    See `run_preparer_llm` — wire it to the Claude Agent SDK.
  - Heuristic mode (runs offline, no API key): a deterministic solver whose
    skills are UNLOCKED BY PRECEDENTS. With no precedents it only escalates;
    once corrections have created precedents, it solves those trap types.
    This lets the whole learning-curve demo run with zero dependencies, and
    it documents exactly what the LLM version must learn to do.

Escalation is always safe: any residual bank line with no defensible ledger
support is routed to the human queue rather than guessed.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from schemas import BankLine, LedgerEntry, Precedent, ProposedMatch

CENTS = 0.005
FEE_TOLERANCE = 50.0        # a "fee-sized" gap between bank and ledger


def _has(precedents: list[Precedent], pattern: str) -> bool:
    return any(p.pattern == pattern for p in precedents)


def run_preparer(
    bank: list[BankLine],
    ledger: list[LedgerEntry],
    precedents: list[Precedent],
) -> list[ProposedMatch]:
    """Heuristic preparer. Skills gated on precedents (see module docstring)."""
    out: list[ProposedMatch] = []
    used_b: set[str] = set()
    used_l: set[str] = set()

    def free_b() -> list[BankLine]:
        return [b for b in bank if b.id not in used_b]

    def free_l() -> list[LedgerEntry]:
        return [l for l in ledger if l.id not in used_l]

    # --- skill: one payment -> many invoices -------------------------------
    if _has(precedents, "one_payment_many_invoices"):
        for b in free_b():
            same_sign = [l for l in free_l() if (l.amount > 0) == (b.amount > 0)]
            # find a small subset summing to the bank line
            for combo in _subsets(same_sign, target=b.amount, k_max=4):
                if len(combo) >= 2:
                    out.append(ProposedMatch(
                        [b.id], [l.id for l in combo], "one_to_many", 0.9,
                        "bank line equals the sum of these ledger entries", by="preparer"))
                    used_b.add(b.id); used_l.update(l.id for l in combo)
                    break

    # --- skill: wire net of fee -------------------------------------------
    if _has(precedents, "wire_net_of_fee"):
        for b in free_b():
            for l in free_l():
                if (l.amount > 0) == (b.amount > 0):
                    gap = abs(abs(l.amount) - abs(b.amount))
                    if CENTS < gap <= FEE_TOLERANCE:
                        out.append(ProposedMatch(
                            [b.id], [l.id], "net_of_fee", 0.85,
                            f"amounts differ by ${gap:.2f}; treat as bank fee", by="preparer"))
                        used_b.add(b.id); used_l.add(l.id)
                        break

    # --- skill: ledger double-book ----------------------------------------
    if _has(precedents, "ledger_double_book"):
        for b in free_b():
            dupes = [l for l in free_l() if abs(abs(l.amount) - abs(b.amount)) < CENTS
                     and (l.amount > 0) == (b.amount > 0)]
            if len(dupes) >= 2:
                out.append(ProposedMatch(
                    [b.id], [l.id for l in dupes[:2]], "duplicate_in_ledger", 0.8,
                    "two ledger entries for one bank line; reverse the duplicate", by="preparer"))
                used_b.add(b.id); used_l.update(l.id for l in dupes[:2])

    # --- skill: timing across period cutoff -------------------------------
    if _has(precedents, "period_cutoff_timing"):
        for b in free_b():
            for l in free_l():
                if abs(l.amount - b.amount) < CENTS:
                    out.append(ProposedMatch(
                        [b.id], [l.id], "timing", 0.8,
                        "amounts tie; dates straddle the period cutoff", by="preparer"))
                    used_b.add(b.id); used_l.add(l.id)
                    break

    # --- safe default: escalate everything left ---------------------------
    for b in free_b():
        out.append(ProposedMatch(
            [b.id], [], "unexplained", 0.2,
            "no defensible ledger support — routing to human review",
            escalate=True, by="preparer"))
        used_b.add(b.id)

    return out


def _subsets(items, target, k_max=4):
    """Yield subsets (size 2..k_max) of items whose amounts sum to target."""
    from itertools import combinations
    for k in range(2, min(k_max, len(items)) + 1):
        for combo in combinations(items, k):
            if abs(sum(l.amount for l in combo) - target) < CENTS:
                yield list(combo)


def run_preparer_llm(bank, ledger, precedents):
    """
    REAL VERSION — wire to the Claude Agent SDK. Sketch:

        from claude_agent_sdk import ClaudeSDKClient, tool
        - system prompt = memory.precedent_prompt(precedents)
        - give it tools: propose_match(bank_ids, ledger_ids, category, rationale),
          escalate(bank_ids, reason), search_ledger(amount, date_window)
        - feed the residual bank + ledger as context
        - collect tool calls into ProposedMatch objects
        - low-confidence / no-candidate -> escalate

    Keep the SAME return type as run_preparer so run.py doesn't care which
    mode is active.
    """
    raise NotImplementedError("wire to Claude Agent SDK; see run_preparer for the target behavior")
