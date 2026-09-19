# Office of the CFO — Agentic Reconciliation

**HackMIT 2026 · Maximor track.** An agentic system that runs a real finance
workflow — **bank reconciliation** — with an agent team, memory that makes it
better over time, and human review on uncertainty. One reconciled payment
flows into the close, the cash forecast, and the audit file, so the same
transaction means the same thing everywhere.

## The one thing to see

```
python run.py
```

Runs two months and prints the **learning curve**:

```
MONTH 1 — cold start        accuracy  69.2%   (0 false matches, 4 punted to human)
  [human review] 4 corrections -> 4 precedents
MONTH 2 — after learning    accuracy 100.0%   (0 false matches)
LEARNING CURVE:  month1 69.2% -> month2 100.0%
```

The system solves the easy matches, **correctly escalates the one unexplained
item instead of guessing**, punts what it hasn't learned to a human — then
learns from the corrections and handles those cases itself next month. That
measured curve, with **zero false matches**, is the differentiator: most teams
show multi-agent theater; almost none show learning you can measure.

Runs **offline, zero dependencies** (heuristic preparer). Swap in the Claude
Agent SDK version for the real thing — same interfaces.

---

## Why this design wins the track

The prompt explicitly rejects one-shot chatbots and extraction pipelines. It
rewards: multi-step reasoning over messy data · memory that changes the next
action · consistency across workflows · human review when uncertain · a real
measure of "better." Each maps to a piece here:

| Judging criterion            | Where it lives |
|------------------------------|----------------|
| Multi-agent team             | `agents/preparer.py`, `agents/auditor.py` (+ reviewer, gated) |
| Memory & self-improvement    | `memory.py` — precedents distilled from corrections |
| Human review on uncertainty  | preparer escalates; scorer credits declining to guess |
| Consistency across workflows | one event stream renders bank + ledger (+ AP) — same txn everywhere |
| Own measure of "better"      | `scorer.py` — deterministic, ground-truth accuracy |
| Connective tissue            | recon updates the cash forecast + audit log |

## Architecture

```
        ONE business-event stream  (generator.py) = single source of truth
                 │ rendered into ▼
        ┌────────────────┬─────────────────┐
        │ bank_statement │ ledger          │   (agent-facing, no provenance)
        └────────────────┴─────────────────┘
                 ▼
        pre-matcher (deterministic, clears ~70% exact)   prematcher.py
                 ▼ residual
        PREPARER agent  ── reads precedents, works the mess, ESCALATES the rest
                 ▼
        AUDITOR agent   ── re-performs, writes citable findings   audit_log.md
                 ▼
        SCORER  ── grades vs ground truth -> scorecard    scorer.py
                 ▼
        HUMAN REVIEW ── corrections -> distill precedents  memory.py
                          (feeds the next month)
```

## The data contract (`schemas.py`) — agree on this at hour 0

Everything speaks these types. **Build against the sample fixtures in
`fixtures/` so nobody is blocked on the generator.**

- `Event` — the shared truth stream (invoice, payment, fee, refund, PO…)
- `BankLine`, `LedgerEntry` — rendered records the agent sees (no provenance)
- `MatchLabel` — ground truth (scorer-only, never shown to agents)
- `ProposedMatch` — what the pre-matcher / preparer / human output
- `Precedent`, `Correction` — memory

**Provenance rule:** which event produced a record lives only in `MatchLabel`,
never in the agent-facing records — that keeps the task honest.

## Work split (4–5 people)

1. **Data + scorer** — `generator.py`, `scorer.py`. Owns ground truth + schema.
2. **Preparer + pre-matcher** — `prematcher.py`, `agents/preparer.py`. Wire
   `run_preparer_llm` to the Claude Agent SDK (same return type as the stub).
3. **Human-review UI + scorecard** — *the product, not polish.* The month1→
   corrections→month2 money-shot is this workstream. Also the audit-log view.
4. **Memory + auditor** — `memory.py`, `agents/auditor.py`. Replace
   `distill()`'s keyword mapping with an LLM that generalizes corrections.
5. **AP three-way match** — *gated:* extend the event stream with PO/invoice
   events now (safe schema work), but no AP *agent* until the recon slice is
   demoable end-to-end. Same event stream renders AP docs → real connective
   tissue, not a second dataset.

## Demo discipline

- **Pre-run & cache month 1; only run month 2 live** — a stalled live agent is
  the #1 demo killer. The `--month` flag persists memory across processes:
  ```
  python run.py --month 1     # before the demo: caches precedents to disk
  python run.py --month 2     # live on stage: loads them, jumps to 100%
  ```
  (`python run.py` with no flag runs the whole curve in one shot.)
- **Person 3 owns a rehearsed 2-minute script** from the midpoint on.
- Integrate continuously against the fixtures — don't meet your code at hour 20.

## Calibration / reference benchmarks

- [Invoice Sandbox Benchmark](https://github.com/ciru-ai/invoice-sandbox-benchmark) — synthetic AP inbox with planted traps
- [APEX-Accounting](https://huggingface.co/datasets/mercor/apex-accounting) — month-end close, rubric-graded
- [DABstep](https://huggingface.co/datasets/adyen/DABstep) — card-payment data, 450 multi-step Qs
- [Finance Agent Benchmark](https://huggingface.co/datasets/vals-ai/finance_agent_benchmark) — filings research
- [Penrose accounting agent](https://accounting.penrose.com/) — reference product

## Files

```
schemas.py          the data contract
generator.py        event stream -> bank + ledger + ground truth (seeded)
prematcher.py       deterministic exact-match pass
scorer.py           deterministic scorecard vs ground truth
memory.py           precedents + corrections (the learning loop)
agents/preparer.py  works the residual; heuristic + LLM-mode sketch
agents/auditor.py   re-performs, writes audit_log.md
run.py              orchestrator — the two-month learning-curve demo
fixtures/           sample records per schema (build against these)
```
