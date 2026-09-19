"""
Deterministic pre-matcher.  (Owner: person 2 — Preparer + pre-matcher)

Plain code, NO LLM. Clears the easy ~70% (exact amount + date within a
window, one-to-one, unambiguous) so the agent only reasons about the messy
residual. This is how real recon tools work, it keeps live demo runs fast,
and it keeps the agent's reasoning visible on the cases that are actually
interesting.

Returns (cleared_matches, residual_bank_lines, residual_ledger_entries).
The residual is what you hand to the preparer agent.
"""

from __future__ import annotations

from datetime import date

from schemas import BankLine, LedgerEntry, ProposedMatch

DATE_WINDOW_DAYS = 2
CENTS = 0.005


def _parse(d: str) -> date:
    y, m, dd = (int(x) for x in d.split("-"))
    return date(y, m, dd)


def prematch(
    bank: list[BankLine],
    ledger: list[LedgerEntry],
    window_days: int = DATE_WINDOW_DAYS,
) -> tuple[list[ProposedMatch], list[BankLine], list[LedgerEntry]]:
    matches: list[ProposedMatch] = []
    used_bank: set[str] = set()
    used_ledger: set[str] = set()

    for b in bank:
        if b.id in used_bank:
            continue
        # candidates: same signed amount (to the cent), within the date window,
        # not already consumed.
        cands = [
            l for l in ledger
            if l.id not in used_ledger
            and abs(l.amount - b.amount) < CENTS
            and abs((_parse(l.date) - _parse(b.date)).days) <= window_days
        ]
        # only auto-clear when the match is UNAMBIGUOUS (exactly one candidate)
        if len(cands) == 1:
            l = cands[0]
            matches.append(ProposedMatch(
                bank_line_ids=[b.id],
                ledger_entry_ids=[l.id],
                category="exact",
                confidence=1.0,
                rationale=f"exact amount {b.amount} within {window_days}d",
                escalate=False,
                by="prematcher",
            ))
            used_bank.add(b.id)
            used_ledger.add(l.id)

    residual_bank = [b for b in bank if b.id not in used_bank]
    residual_ledger = [l for l in ledger if l.id not in used_ledger]
    return matches, residual_bank, residual_ledger


if __name__ == "__main__":
    from generator import generate
    c = generate(month=1)
    cleared, rb, rl = prematch(c.bank_statement, c.ledger)
    print(f"pre-matcher cleared {len(cleared)} / {len(c.bank_statement)} bank lines")
    print(f"residual: {len(rb)} bank lines, {len(rl)} ledger entries -> to the agent")
