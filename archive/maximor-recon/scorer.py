"""
Deterministic scorer.  (Owner: person 1 — Data + scorer)

Grades a set of ProposedMatch against ground-truth MatchLabel. Because both
records were rendered from one event stream, this is exact — which is what
makes "accuracy went from X% to Y%" a defensible number in the demo.

A proposed match is CORRECT when its set of bank-line ids and set of
ledger-entry ids exactly equal a (non-escalate) label group. The unexplained
trap is scored specially: it is correct ONLY if the system escalated it and
did NOT invent a match for it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from schemas import BankLine, MatchLabel, ProposedMatch


@dataclass
class Scorecard:
    total_groups: int = 0
    correct: int = 0
    wrong: int = 0                  # FALSE match: proposed a confident match that is not real
    missed: int = 0                 # label group nobody resolved (incl. over-escalations)
    over_escalated: int = 0         # punted a solvable group to a human (conservative, not a false match)
    escalations_correct: int = 0    # should-escalate traps handled right
    escalations_expected: int = 0
    dollars_unexplained: float = 0.0
    notes: list[str] = field(default_factory=list)

    @property
    def accuracy(self) -> float:
        # a group is resolved correctly if it was matched (non-escalate) OR
        # correctly escalated — declining to guess an unexplained item counts.
        if not self.total_groups:
            return 0.0
        return round((self.correct + self.escalations_correct) / self.total_groups, 3)

    def render(self) -> str:
        lines = [
            "┌─ SCORECARD ─────────────────────────────────",
            f"│ accuracy            {self.accuracy:>6.1%}  ({self.correct + self.escalations_correct}/{self.total_groups} groups)",
            f"│ wrong (false) match {self.wrong:>6}",
            f"│ over-escalated      {self.over_escalated:>6}  (punted to human)",
            f"│ missed groups       {self.missed:>6}",
            f"│ escalations         {self.escalations_correct:>6} / {self.escalations_expected} correct",
            f"│ $ unexplained       {self.dollars_unexplained:>9.2f}",
            "└─────────────────────────────────────────────",
        ]
        for note in self.notes:
            lines.append(f"  • {note}")
        return "\n".join(lines)


def _key(bank_ids, ledger_ids) -> tuple:
    return (frozenset(bank_ids), frozenset(ledger_ids))


def score(proposed: list[ProposedMatch], labels: list[MatchLabel],
          bank: list[BankLine] | None = None) -> Scorecard:
    sc = Scorecard(total_groups=len(labels))
    amt_by_bank = {b.id: b.amount for b in (bank or [])}
    label_by_key = {_key(l.bank_line_ids, l.ledger_entry_ids): l for l in labels}
    escalate_bank_ids = {b for l in labels if l.should_escalate for b in l.bank_line_ids}
    sc.escalations_expected = sum(1 for l in labels if l.should_escalate)

    # $ unexplained = |amount| of every bank line the system routed to a human
    # (open items pending review). Drops as the system learns to resolve more.
    sc.dollars_unexplained = round(sum(
        abs(amt_by_bank.get(bid, 0.0))
        for p in proposed if p.escalate for bid in p.bank_line_ids
    ), 2)

    matched_keys: set = set()

    for p in proposed:
        # escalation is a valid "resolution" of an unexplained trap
        if p.escalate and set(p.bank_line_ids) & escalate_bank_ids:
            sc.escalations_correct += 1
            for l in labels:
                if l.should_escalate and set(l.bank_line_ids) & set(p.bank_line_ids):
                    matched_keys.add(_key(l.bank_line_ids, l.ledger_entry_ids))
            continue

        # a conservative escalation that didn't hit a real trap = over-escalation,
        # not a false match. It's a miss (counted below), not a wrong answer.
        if p.escalate:
            sc.over_escalated += 1
            continue

        key = _key(p.bank_line_ids, p.ledger_entry_ids)
        lbl = label_by_key.get(key)
        if lbl and not lbl.should_escalate:
            sc.correct += 1
            matched_keys.add(key)
        else:
            # a CONFIDENT match that isn't real is the costly failure
            sc.wrong += 1
            if set(p.bank_line_ids) & escalate_bank_ids:
                sc.notes.append(f"guessed a match on an unexplained item ({p.bank_line_ids})")

    for l in labels:
        if _key(l.bank_line_ids, l.ledger_entry_ids) not in matched_keys:
            sc.missed += 1

    if sc.escalations_correct == sc.escalations_expected and sc.escalations_expected:
        sc.notes.append("unexplained item correctly escalated to human queue")

    return sc


if __name__ == "__main__":
    from generator import generate
    from prematcher import prematch
    c = generate(month=1)
    cleared, rb, rl = prematch(c.bank_statement, c.ledger)
    print("Scoring PRE-MATCHER ONLY (no agent yet):")
    print(score(cleared, c.labels, c.bank_statement).render())
