"""
Synthetic real decisions.  (extends the hand-written seed corpus.)

Generates ~60 FULL `Decision` objects — statement, owner, source, verbatim
evidence, topic — that are ingested into the Brain like any other decision.
Unlike the display-only fake backdrop (`fake_graph.py`), these are real: they
open in the drawer, carry evidence, and flow through relate()/attention.

Topics are `{base}-{sub}` where base comes from the fake backdrop's topic set,
so they cluster with it in the graph. Same-topic collisions across dates let
relate() form organic supersede/conflict chains; a slice are left unowned so
the attention queue stays realistically busy.
"""

from __future__ import annotations

import random

from company_brain.fake_graph import OWNERS, TOPICS
from company_brain.schema import Decision, Evidence, Source

SUBS = ["cdn", "db", "sso", "billing", "mobile", "sla", "schema", "gateway",
        "retention", "rollout", "vendor", "cadence", "registry", "portal",
        "tiers", "oncall", "flags", "lake", "staging", "review", "quotas",
        "webhooks", "caching", "search"]
VERBS = ["Adopt", "Standardize on", "Migrate to", "Deprecate", "Roll out",
         "Consolidate", "Sunset", "Pilot", "Approve", "Rework", "Outsource"]
OBJECTS = ["the billing service", "the design system", "the on-call rotation",
           "the data lake", "feature flags", "the CDN", "the staging env",
           "SSO", "the pricing tiers", "the mobile SDK", "log retention",
           "the release cadence", "the API gateway", "the model registry",
           "the partner portal", "the analytics schema", "vendor contracts",
           "rate limits", "the search index", "the caching layer"]
CHANNELS = ["#engineering", "#product", "#platform", "#security", "#data"]


def _date(rng) -> str:
    y = rng.choice([2025, 2026])
    m = rng.randint(1, 12) if y == 2025 else rng.randint(1, 9)
    return f"{y}-{m:02d}-{rng.randint(1, 28):02d}"


def generate_decisions(n: int = 60, seed: int = 11) -> list[Decision]:
    rng = random.Random(seed)
    out: list[Decision] = []
    for i in range(n):
        base = rng.choice(TOPICS)
        topic = f"{base}-{rng.choice(SUBS)}"
        stmt = f"{rng.choice(VERBS)} {rng.choice(OBJECTS)}"
        owner = rng.choice(OWNERS) if rng.random() > 0.18 else None
        who = owner or "team"
        date = _date(rng)
        link = f"https://slack.example.com/{base}/p{i:04d}"
        quote = f"{who}: we decided to {stmt[0].lower()}{stmt[1:].lower()}. " \
                f"{'I will own it.' if owner else 'nobody owns this yet.'}"
        out.append(Decision(
            id=f"SYN-{i:03d}",
            statement=stmt,
            owner=owner,
            decided_on=date,
            source=Source(type="slack", link=link),
            evidence=[Evidence(verbatim_quote=quote, link=link)],
            topic=topic,
        ))
    # ingest oldest-first so relate() builds supersede chains correctly
    out.sort(key=lambda d: d.decided_on)
    return out
