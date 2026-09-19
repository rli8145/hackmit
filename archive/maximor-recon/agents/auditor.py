"""
Auditor agent.  (Owner: person 4 — Memory + auditor)

Independent second pass. Re-performs the reconciliation result and writes
findings — the artifact that makes the system "defensible to an auditor,"
which the challenge explicitly rewards. It does NOT trust the preparer; it
checks the work and cites evidence.

Findings it should raise:
  - any bank line the system claims to have matched but the math doesn't tie
  - self-approved / round-number / duplicate-vendor style controls (extend me)
  - the escalated unexplained item, restated as an open item with $ amount

Writes to audit_log.md so the demo can show a real, citable trail.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from schemas import BankLine, LedgerEntry, ProposedMatch

CENTS = 0.005
AUDIT_LOG = os.path.join(os.path.dirname(os.path.dirname(__file__)), "audit_log.md")


def audit(
    matches: list[ProposedMatch],
    bank: list[BankLine],
    ledger: list[LedgerEntry],
    period: str,
) -> list[str]:
    b_by = {b.id: b for b in bank}
    l_by = {l.id: l for l in ledger}
    findings: list[str] = []

    for m in matches:
        if m.escalate:
            amt = sum(abs(b_by[i].amount) for i in m.bank_line_ids if i in b_by)
            findings.append(f"OPEN ITEM: ${amt:.2f} escalated to human review "
                            f"({', '.join(m.bank_line_ids)}) — {m.rationale}")
            continue
        # re-perform: for a well-formed match the ledger side should tie to
        # the bank side (allowing a fee gap for net_of_fee).
        bsum = sum(b_by[i].amount for i in m.bank_line_ids if i in b_by)
        lsum = sum(l_by[i].amount for i in m.ledger_entry_ids if i in l_by)
        gap = abs(abs(bsum) - abs(lsum))
        if m.category == "net_of_fee":
            if gap > 50.0:
                findings.append(f"FINDING: net_of_fee gap ${gap:.2f} exceeds fee tolerance "
                                f"({m.bank_line_ids} vs {m.ledger_entry_ids})")
        elif m.category == "duplicate_in_ledger":
            findings.append(f"CONTROL: duplicate booking flagged for reversal "
                            f"({m.ledger_entry_ids}); confirm one entry removed")
        elif gap > CENTS:
            findings.append(f"FINDING: match does not tie — bank ${bsum:.2f} vs "
                            f"ledger ${lsum:.2f} ({m.bank_line_ids})")

    _write_log(period, matches, findings)
    return findings


def _write_log(period, matches, findings) -> None:
    lines = [f"# Audit log — {period}", "",
             f"Matches reviewed: {len(matches)}",
             f"Findings: {len(findings)}", ""]
    lines += [f"- {f}" for f in findings] or ["- No exceptions."]
    with open(AUDIT_LOG, "w") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    print("auditor module — imported by run.py")
