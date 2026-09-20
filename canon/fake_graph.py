"""
Synthetic large-graph generator — makes the canon look like a mature org.

Produces ~1000 decision-like nodes clustered into topic groups with edges
(supersedes / depends_on / conflicts), so the graph view reads like a real
company's institutional memory (Obsidian-style). Deterministic (seeded).

Purely for the visualization. The real 7 decisions (with attention, evidence,
etc.) come from Canon; these fake nodes are display-only and marked
`real: false`.
"""

from __future__ import annotations

import random

TOPICS = [
    "infrastructure", "pricing", "hiring", "security", "data-platform",
    "ml-models", "public-api", "frontend", "mobile", "compliance",
    "marketing", "sales", "support", "devops", "billing", "auth",
    "analytics", "roadmap", "partnerships", "legal",
]
OWNERS = ["priya", "sam", "dan", "maya", "alex", "jordan", "lee", "kim",
          "noah", "ava", "ravi", "chen", "omar", "sofia", "iris", "theo"]
VERBS = ["Adopt", "Standardize on", "Migrate to", "Deprecate", "Roll out",
         "Consolidate", "Sunset", "Pilot", "Approve", "Freeze", "Rework",
         "Outsource", "Insource", "Rename", "Split", "Merge"]
OBJECTS = ["the billing service", "vendor contracts", "the design system",
           "on-call rotation", "the data lake", "feature flags", "the CDN",
           "the staging env", "SSO", "the pricing tiers", "the mobile SDK",
           "log retention", "the review process", "the release cadence",
           "the API gateway", "the model registry", "the support SLA",
           "the analytics schema", "the partner portal", "the audit trail"]
STATUS_WEIGHTS = [("live", 0.68), ("needs_review", 0.22), ("superseded", 0.10)]


def _weighted(rng, weights):
    r, acc = rng.random(), 0.0
    for val, w in weights:
        acc += w
        if r <= acc:
            return val
    return weights[-1][0]


def generate(n: int = 1000, seed: int = 7) -> dict:
    rng = random.Random(seed)
    nodes: list[dict] = []
    edges: list[dict] = []

    # spread n across topics into clusters
    per = max(6, n // len(TOPICS))
    idx = 0
    for topic in TOPICS:
        cluster_start = idx
        size = per + rng.randint(-4, 8)
        for _ in range(size):
            if idx >= n:
                break
            nid = f"FAKE-{idx:04d}"
            nodes.append({
                "id": nid,
                "statement": f"{rng.choice(VERBS)} {rng.choice(OBJECTS)}",
                "status": _weighted(rng, STATUS_WEIGHTS),
                "owner": (rng.choice(OWNERS) if rng.random() > 0.15 else None),
                "topic": topic,
                "real": False,
            })
            # connect into the cluster (spanning tree) so groups stay cohesive,
            # plus extra intra-cluster links for a dense, webby blob
            if idx > cluster_start:
                links = 1 + (1 if rng.random() < 0.6 else 0) + (1 if rng.random() < 0.25 else 0)
                for _ in range(links):
                    tgt = rng.randint(cluster_start, idx - 1)
                    etype = rng.choices(["depends_on", "supersedes", "conflicts"],
                                        weights=[6, 3, 1])[0]
                    edges.append({"source": nid, "type": etype,
                                  "target": f"FAKE-{tgt:04d}"})
            idx += 1

    # sparse cross-cluster links (real orgs have them) — kept few so hub
    # islands stay visually distinct
    for _ in range(n // 45):
        a, b = rng.randint(0, idx - 1), rng.randint(0, idx - 1)
        if a != b:
            edges.append({"source": f"FAKE-{a:04d}", "type": "depends_on",
                          "target": f"FAKE-{b:04d}"})

    return {"nodes": nodes, "edges": edges, "count": idx}
