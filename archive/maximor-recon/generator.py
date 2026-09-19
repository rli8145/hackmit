"""
Event-stream generator + renderers.  (Owner: person 1 — Data + scorer)

Generates ONE business-event stream for a synthetic company, then renders:
  - bank_statement : list[BankLine]     (agent-facing, clean)
  - ledger         : list[LedgerEntry]  (agent-facing, clean)
  - labels         : list[MatchLabel]   (ground truth, scorer-only)

Traps are planted by *perturbing the rendering* of true events, so every
trap still has a correct ground-truth answer:

  exact                one clean deposit/payment                (pre-matcher clears)
  one_to_many          one customer payment covering 3 invoices
  net_of_fee           a wire that lands net of a bank fee
  duplicate_in_ledger  a refund the ledger booked twice
  timing               a payment booked in-period, cleared next period
  unexplained          a mystery bank debit with NO ledger + NO cause  -> ESCALATE

Seeded so runs are reproducible (month 1 can be cached for the demo).
Pass a different `month` to get the same trap *shapes* with fresh numbers,
so month 2 exercises the precedents learned in month 1.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, timedelta

from schemas import BankLine, Event, LedgerEntry, MatchLabel

CUSTOMERS = ["Northwind Traders", "Contoso Ltd", "Fabrikam Inc", "Tailspin Toys"]
VENDORS = ["Acme Supply", "Globex Cloud", "Initech Payroll", "Umbrella Logistics"]
CASH = "1000 Cash"


@dataclass
class Company:
    """A generated period: the truth stream + the two rendered records + labels."""
    name: str
    period: str                     # e.g. "2026-01"
    events: list[Event]
    bank_statement: list[BankLine]
    ledger: list[LedgerEntry]
    labels: list[MatchLabel]


def generate(month: int = 1, seed: int | None = None) -> Company:
    rng = random.Random(seed if seed is not None else 1000 + month)
    ym = f"2026-{month:02d}"

    def d(day: int) -> str:
        return f"{ym}-{day:02d}"

    events: list[Event] = []
    bank: list[BankLine] = []
    ledger: list[LedgerEntry] = []
    labels: list[MatchLabel] = []

    n = {"e": 0, "b": 0, "l": 0, "g": 0}

    def eid() -> str:
        n["e"] += 1; return f"EV-{month}-{n['e']:03d}"

    def bid() -> str:
        n["b"] += 1; return f"BANK-{month}-{n['b']:03d}"

    def lid() -> str:
        n["l"] += 1; return f"GL-{month}-{n['l']:03d}"

    def gid() -> str:
        n["g"] += 1; return f"GRP-{month}-{n['g']:03d}"

    def money(lo: float, hi: float) -> float:
        return round(rng.uniform(lo, hi), 2)

    # --- 8 clean exact matches (the ~70% the pre-matcher should auto-clear) ---
    for _ in range(8):
        day = rng.randint(2, 26)
        amt = money(200, 5000)
        inflow = rng.random() < 0.5
        party = rng.choice(CUSTOMERS if inflow else VENDORS)
        ev = Event(eid(), "payment_received" if inflow else "payment_sent",
                   d(day), amt, party)
        events.append(ev)
        sign = 1 if inflow else -1
        b = BankLine(bid(), d(day), sign * amt,
                     f"{'ACH CREDIT' if inflow else 'ACH DEBIT'} {party.upper()}")
        l = LedgerEntry(lid(), d(day), CASH, sign * amt,
                        f"{'Receipt from' if inflow else 'Payment to'} {party}")
        bank.append(b); ledger.append(l)
        labels.append(MatchLabel(gid(), [b.id], [l.id], "exact",
                                 "1:1 exact match", False))

    # --- one_to_many: one customer payment covers three invoices ---
    cust = rng.choice(CUSTOMERS)
    parts = [money(300, 1500) for _ in range(3)]
    total = round(sum(parts), 2)
    day = rng.randint(5, 24)
    events.append(Event(eid(), "payment_received", d(day), total, cust,
                        meta={"covers_invoices": 3}))
    b = BankLine(bid(), d(day), total, f"ACH CREDIT {cust.upper()} REF BULK")
    ls = [LedgerEntry(lid(), d(day), "1200 A/R", p, f"Invoice paid — {cust}")
          for p in parts]
    bank.append(b); ledger.extend(ls)
    labels.append(MatchLabel(gid(), [b.id], [l.id for l in ls], "one_to_many",
                             f"one ${total} deposit clears 3 invoices", False))

    # --- net_of_fee: wire lands net of a $15 wire fee ---
    cust = rng.choice(CUSTOMERS)
    gross = money(2000, 6000)
    fee = 15.00
    net = round(gross - fee, 2)
    day = rng.randint(5, 24)
    events.append(Event(eid(), "payment_received", d(day), gross, cust,
                        meta={"wire_fee": fee}))
    b = BankLine(bid(), d(day), net, f"WIRE IN {cust.upper()} (NET OF FEE)")
    l = LedgerEntry(lid(), d(day), "1200 A/R", gross, f"Wire from {cust}")
    bank.append(b); ledger.append(l)
    labels.append(MatchLabel(gid(), [b.id], [l.id], "net_of_fee",
                             f"${gross} ledger vs ${net} bank; ${fee} wire fee", False))

    # --- duplicate_in_ledger: refund booked twice in the ledger ---
    vend = rng.choice(VENDORS)
    ramt = money(100, 800)
    day = rng.randint(5, 24)
    events.append(Event(eid(), "refund", d(day), ramt, vend, meta={"duplicated": True}))
    b = BankLine(bid(), d(day), ramt, f"REFUND {vend.upper()}")
    l1 = LedgerEntry(lid(), d(day), CASH, ramt, f"Refund from {vend}")
    l2 = LedgerEntry(lid(), d(day + 1), CASH, ramt, f"Refund from {vend} (dup?)")
    bank.append(b); ledger.extend([l1, l2])
    labels.append(MatchLabel(gid(), [b.id], [l1.id, l2.id], "duplicate_in_ledger",
                             "ledger double-booked; keep one, reverse the other", False))

    # --- timing: payment booked in-period, clears early next period ---
    vend = rng.choice(VENDORS)
    amt = money(500, 2500)
    events.append(Event(eid(), "payment_sent", d(28), amt, vend, meta={"timing": True}))
    l = LedgerEntry(lid(), d(28), CASH, -amt, f"Payment to {vend}")
    # clears 5 days later — deliberately OUTSIDE the pre-matcher's date window
    # every month, so the timing precedent is genuinely exercised (not a
    # calendar accident where +2 days happens to fall inside the window).
    clear = date(2026, month, 28) + timedelta(days=5)
    b = BankLine(bid(), clear.isoformat(), -amt, f"ACH DEBIT {vend.upper()}")
    bank.append(b); ledger.append(l)
    labels.append(MatchLabel(gid(), [b.id], [l.id], "timing",
                             "booked M-end, cleared M+1; timing difference", False))

    # --- unexplained: mystery debit, no ledger, no cause -> MUST escalate ---
    myst = 12.40
    day = rng.randint(10, 20)
    b = BankLine(bid(), d(day), -myst, "MISC DEBIT 4471 — NO REF")
    bank.append(b)
    labels.append(MatchLabel(gid(), [b.id], [], "unexplained",
                             f"${myst} debit with no ledger support — escalate, do NOT guess",
                             True))

    rng.shuffle(bank)
    rng.shuffle(ledger)

    return Company("Vertex Robotics Inc", ym, events, bank, ledger, labels)


if __name__ == "__main__":
    c = generate(month=1)
    print(f"{c.name} — {c.period}")
    print(f"  events={len(c.events)}  bank_lines={len(c.bank_statement)}  "
          f"ledger_entries={len(c.ledger)}  match_groups={len(c.labels)}")
    from collections import Counter
    print("  trap mix:", dict(Counter(l.category for l in c.labels)))
