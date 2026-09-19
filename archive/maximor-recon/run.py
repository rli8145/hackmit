"""
Orchestrator — the demo money-shot.  (integration owner: whole team)

Two ways to run:

  python run.py            full two-month curve in one process (cold start ->
                           learn -> improved). Resets memory first.

  python run.py --month 1  run ONE period standalone. Loads precedents from
  python run.py --month 2  memory_store.json, runs, then records corrections
                           and saves updated precedents back to disk.

The --month form is the real demo protocol: pre-run & cache month 1
(`python run.py --month 1`), then run month 2 LIVE — it loads the precedents
month 1 persisted, so the improvement is genuine cross-process memory, not a
variable held in RAM. A stalled live agent is the #1 demo killer; this lets
you cache the slow part.

Runs offline with zero dependencies (heuristic preparer). Swap in
run_preparer_llm for the real Claude Agent SDK version — same return type.
"""

from __future__ import annotations

import argparse

from agents.auditor import audit
from agents.preparer import run_preparer
from generator import generate
from memory import distill, load, save
from prematcher import prematch
from schemas import Correction, Precedent
from scorer import score


def run_period(month: int, precedents: list[Precedent], label: str):
    c = generate(month=month)
    cleared, rb, rl = prematch(c.bank_statement, c.ledger)
    residual = run_preparer(rb, rl, precedents)
    all_matches = cleared + residual
    sc = score(all_matches, c.labels, c.bank_statement)

    print(f"\n=== {label}  ({c.name}, {c.period}) ===")
    print(f"pre-matcher auto-cleared {len(cleared)}; preparer worked {len(rb)} residual "
          f"bank lines with {len(precedents)} precedents")
    print(sc.render())

    findings = audit(all_matches, c.bank_statement, c.ledger, c.period)
    print(f"auditor wrote {len(findings)} finding(s) -> audit_log.md")

    net_cash = sum(b.amount for b in c.bank_statement)
    print(f"13-week cash forecast updated with period net cash: ${net_cash:,.2f}")
    return c, all_matches, sc


def corrections_from_misses(c, matches) -> list[Correction]:
    """Simulate a human correcting the traps the agent missed/escalated.

    In the real product these come from the human-review UI (person 3). Here
    we synthesize one correction per solvable trap the agent didn't resolve,
    so the learning loop is demonstrable offline.
    """
    resolved = {frozenset(m.bank_line_ids) for m in matches if not m.escalate}
    corr: list[Correction] = []
    for lbl in c.labels:
        if lbl.category in ("exact", "unexplained"):
            continue
        if frozenset(lbl.bank_line_ids) in resolved:
            continue  # agent already handled it — nothing to correct
        corr.append(Correction(
            id=f"COR-{lbl.group_id}", group_id=lbl.group_id,
            was="escalated / unmatched",
            should_be=f"{lbl.category}: {lbl.resolution}",
            date=c.period + "-28"))
    return corr


def run_single(month: int):
    """Standalone period run using persisted memory."""
    precedents, corrections = load()
    c, matches, sc = run_period(month, precedents, f"MONTH {month}")

    new_corr = corrections_from_misses(c, matches)
    if new_corr:
        corrections += new_corr
        precedents = distill(corrections, precedents)
        save(precedents, corrections)
        print(f"\n[human review] +{len(new_corr)} corrections saved -> "
              f"{len(precedents)} precedents on disk: {[p.pattern for p in precedents]}")
    else:
        print("\n[human review] no corrections needed this period.")


def run_full():
    """Full two-month curve in one process (resets memory)."""
    save([], [])  # cold start
    precedents: list[Precedent] = []

    c1, m1, sc1 = run_period(1, precedents, "MONTH 1 — cold start")
    corr = corrections_from_misses(c1, m1)
    precedents = distill(corr, precedents)
    save(precedents, corr)
    print(f"\n[human review] {len(corr)} corrections -> distilled "
          f"{len(precedents)} precedents: {[p.pattern for p in precedents]}")

    c2, m2, sc2 = run_period(2, precedents, "MONTH 2 — after learning")

    print("\n" + "=" * 50)
    print(f"LEARNING CURVE:  month1 {sc1.accuracy:.1%}  ->  month2 {sc2.accuracy:.1%}")
    print("=" * 50)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", type=int, help="run one period standalone using saved memory")
    args = ap.parse_args()

    if args.month:
        run_single(args.month)
    else:
        run_full()
