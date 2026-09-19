"""
THE DATA CONTRACT  (hour-0 file — agree on this before anyone writes code)
=========================================================================

Everything in the system speaks these types. The generator PRODUCES them,
the pre-matcher and agents CONSUME them, the scorer GRADES against them.

Design rule that makes the whole demo trustworthy:
    ONE business-event stream is the single source of truth. The bank
    statement and the ledger are both *rendered* from that stream. Because
    of that, ground-truth match labels come for free — the scorer is
    deterministic, so "accuracy went from X% to Y%" is a real number, not
    a vibe.

Provenance rule:
    Agent-facing records (BankLine, LedgerEntry) DO NOT carry which event
    produced them. Provenance lives only in MatchLabel (ground truth) and
    is never shown to the agents. This keeps the task honest.

Zero dependencies on purpose: the deterministic core (schemas, generator,
pre-matcher, scorer) runs on stdlib alone so anyone can `python run.py`
with no install. Only the LLM agents need `anthropic` / the Agent SDK.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


# ---------------------------------------------------------------------------
# 1. Business events — the shared source of truth
# ---------------------------------------------------------------------------

# One event type covers the cash + AP/AR life-cycle. `meta` carries
# type-specific fields (po_id, fee, linked invoices, trap tag) so the
# generator and renderers stay simple.
EVENT_TYPES = (
    "invoice_issued",     # AR: we bill a customer (we are owed money)
    "payment_received",   # AR: customer pays us   -> bank deposit + ledger credit
    "purchase_order",     # AP: we order from a vendor
    "invoice_received",   # AP: vendor bills us
    "payment_sent",       # AP: we pay a vendor    -> bank withdrawal + ledger debit
    "bank_fee",           # bank charges a fee
    "refund",             # money returned (either direction)
)


@dataclass
class Event:
    id: str
    type: str                       # one of EVENT_TYPES
    date: str                       # ISO date "YYYY-MM-DD"
    amount: float                   # always positive; direction is per-type
    party: str                      # customer or vendor name
    links: list[str] = field(default_factory=list)   # related event ids
    meta: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 2. Rendered records — what the agent actually sees (NO provenance)
# ---------------------------------------------------------------------------

@dataclass
class BankLine:
    id: str
    date: str                       # date it cleared the bank
    amount: float                   # SIGNED: + deposit, - withdrawal
    description: str                # messy, bank-style free text


@dataclass
class LedgerEntry:
    id: str
    date: str                       # date we booked it
    account: str                    # GL account name
    amount: float                   # SIGNED: + debit-to-cash, - credit
    memo: str


# ---------------------------------------------------------------------------
# 3. Ground truth — how bank lines and ledger entries actually relate
# ---------------------------------------------------------------------------

# category values, also used by ProposedMatch:
MATCH_CATEGORIES = (
    "exact",              # 1 bank line <-> 1 ledger entry, same amount/date
    "one_to_many",        # 1 bank line <-> N ledger entries (one payment, many invoices)
    "net_of_fee",         # amounts differ by a bank/wire/processor fee
    "duplicate_in_ledger",# ledger booked something twice; bank shows it once
    "timing",             # same txn, dates straddle the period cutoff
    "unexplained",        # no valid match — MUST be escalated, never guessed
)


@dataclass
class MatchLabel:
    """Ground truth. Never shown to agents; used only by the scorer."""
    group_id: str
    bank_line_ids: list[str]
    ledger_entry_ids: list[str]
    category: str                   # one of MATCH_CATEGORIES
    resolution: str                 # human-readable expected outcome
    should_escalate: bool           # True only for 'unexplained' style traps


# ---------------------------------------------------------------------------
# 4. Output — what the pre-matcher / preparer / human produce
# ---------------------------------------------------------------------------

@dataclass
class ProposedMatch:
    bank_line_ids: list[str]
    ledger_entry_ids: list[str]
    category: str                   # one of MATCH_CATEGORIES
    confidence: float               # 0..1 ; low -> route to human
    rationale: str                  # why the system believes this
    escalate: bool = False          # True = send to human queue, don't auto-clear
    by: str = "preparer"            # "prematcher" | "preparer" | "human" | "auditor"


# ---------------------------------------------------------------------------
# 5. Memory — the differentiator. Precedents + corrections.
# ---------------------------------------------------------------------------

@dataclass
class Correction:
    """A human fixing the agent. The raw material of learning."""
    id: str
    group_id: str                   # which recon item was wrong
    was: str                        # what the agent did
    should_be: str                  # what the human said is correct
    date: str


@dataclass
class Precedent:
    """A reusable rule distilled from one or more corrections.

    The preparer reads all precedents at run start and applies them before
    reasoning from scratch. This is what makes month 2 better than month 1.
    Deliberately a plain file, not a memory framework — same demo, no rabbit
    hole.
    """
    id: str
    pattern: str                    # short tag, e.g. "wire_net_of_fee"
    description: str                # when this applies
    rule: str                       # instruction the preparer follows
    created_from: list[str] = field(default_factory=list)  # correction ids
    hits: int = 0                   # times applied (shows it's earning its keep)


# ---------------------------------------------------------------------------
# JSON helpers — keep serialization in one place so the contract stays stable
# ---------------------------------------------------------------------------

def to_dict(obj: Any) -> dict:
    return asdict(obj)


def dump_list(objs: list[Any]) -> list[dict]:
    return [asdict(o) for o in objs]


def load_list(cls, rows: list[dict]) -> list[Any]:
    return [cls(**row) for row in rows]
