"""
Synthetic seed corpus.  (Owner: Andrew / P1.)

A fictional company (Vertex Robotics) talking in Slack, meetings, and notes.
Fully synthetic — NO real company data. Decisions are planted so the graph has
the four attention triggers to catch:

  supersession   AWS -> GCP infra; free-tier 100 -> 50 calls
  conflict       two live statements on the free tier before it's reconciled
  unowned        the Q2 hiring decision and the Pro pricing decision
  assumption     Pro price assumes "AWS infra costs" — which later moved to GCP
     drift

Each source carries ground-truth `labels` so eval.py can score extraction and
conflict detection with real numbers.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from company_brain.schema import LabeledDecision


@dataclass
class SeedSource:
    id: str
    type: str            # slack | fellow | notion | paste
    link: str
    date: str            # ISO
    origin: str          # channel / meeting / doc title
    text: str
    labels: list[LabeledDecision] = field(default_factory=list)


SOURCES: list[SeedSource] = [
    SeedSource(
        id="SRC-01", type="slack", date="2026-01-10",
        origin="#engineering",
        link="https://slack.example.com/eng/p101",
        text=(
            "priya: infra decision for launch — we're going with AWS, region "
            "us-east-1. it's what we all know and we can move fast.\n"
            "dan: works for me.\n"
            "priya: decided then. I'll own the AWS setup."
        ),
        labels=[LabeledDecision(
            statement_gist="deploy on AWS us-east-1",
            topic="infrastructure", owner="priya",
            should_be_unowned=False, relation="none")],
    ),
    SeedSource(
        id="SRC-02", type="slack", date="2026-01-20",
        origin="#product",
        link="https://slack.example.com/product/p120",
        text=(
            "sam: locking the free tier. we'll give 100 API calls/day on free.\n"
            "sam: decision: free tier = 100 calls/day. I'll own it."
        ),
        labels=[LabeledDecision(
            statement_gist="free tier is 100 API calls per day",
            topic="pricing-free-tier", owner="sam",
            should_be_unowned=False, relation="none")],
    ),
    SeedSource(
        id="SRC-03", type="paste", date="2026-02-05",
        origin="pricing working notes",
        link="paste://pricing-notes-0205",
        text=(
            "Pricing sync notes.\n"
            "- We decided to price Pro at $49/month.\n"
            "- This assumes our AWS infra costs stay around current levels.\n"
            "- Owner: TBD (nobody grabbed this yet)."
        ),
        labels=[LabeledDecision(
            statement_gist="price Pro plan at $49 per month",
            topic="pricing-pro", owner=None,
            should_be_unowned=True, relation="none")],
    ),
    SeedSource(
        id="SRC-04", type="fellow", date="2026-02-14",
        origin="Architecture sync (Fellow transcript)",
        link="https://fellow.example.com/arch-0214",
        text=(
            "Priya: the AWS bill is getting scary. I've been modeling GCP and "
            "it's meaningfully cheaper for our workload.\n"
            "Dan: so we move?\n"
            "Priya: yes — we decided to migrate our infrastructure to GCP. "
            "That supersedes the earlier AWS call. I'll own the migration."
        ),
        labels=[LabeledDecision(
            statement_gist="migrate infrastructure to GCP",
            topic="infrastructure", owner="priya",
            should_be_unowned=False, relation="supersedes")],
    ),
    SeedSource(
        id="SRC-05", type="slack", date="2026-02-20",
        origin="#hiring",
        link="https://slack.example.com/hiring/p220",
        text=(
            "dan: we decided to hire 2 backend engineers in Q2 to keep up with "
            "the roadmap.\n"
            "dan: nobody's assigned to drive this yet — we should fix that."
        ),
        labels=[LabeledDecision(
            statement_gist="hire two backend engineers in Q2",
            topic="hiring", owner=None,
            should_be_unowned=True, relation="none")],
    ),
    SeedSource(
        id="SRC-06", type="slack", date="2026-03-02",
        origin="#product",
        link="https://slack.example.com/product/p302",
        text=(
            "sam: usage costs are higher than planned. we're changing the free "
            "tier — decision: free tier = 50 calls/day going forward.\n"
            "sam: I'll own it."
        ),
        labels=[LabeledDecision(
            statement_gist="free tier is 50 API calls per day",
            topic="pricing-free-tier", owner="sam",
            should_be_unowned=False, relation="supersedes")],
    ),
    SeedSource(
        id="SRC-07", type="slack", date="2026-03-10",
        origin="#engineering",
        link="https://slack.example.com/eng/p310",
        text=(
            "dan: we decided to standardize on Python 3.12 across all services.\n"
            "dan: I'll own the upgrade."
        ),
        labels=[LabeledDecision(
            statement_gist="standardize on Python 3.12",
            topic="tech-stack", owner="dan",
            should_be_unowned=False, relation="none")],
    ),
]


def all_labels() -> list[LabeledDecision]:
    return [lbl for s in SOURCES for lbl in s.labels]
