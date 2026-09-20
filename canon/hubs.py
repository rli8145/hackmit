"""
Context hubs — the org's decision graph organized into named clusters.

Every decision belongs to a **hub** (Backend, Frontend, Finance, …) that
divides into **subclusters** (the topic). Hubs give the graph human-readable
regions and give agents a coarse index to navigate by: "show me open Finance
decisions" without reading 1000 nodes.

Agent- and human-friendly: the hub/subcluster live on every node in the graph
payload, and the UI colors + groups by hub.
"""

from __future__ import annotations

# base topic word -> hub
HUB_OF = {
    # Backend
    "infrastructure": "Backend", "api": "Backend", "public-api": "Backend",
    "auth": "Backend", "devops": "Backend", "tech": "Backend",
    "tech-stack": "Backend",
    # Frontend
    "frontend": "Frontend", "mobile": "Frontend", "design": "Frontend",
    # Data & ML
    "data": "Data & ML", "data-platform": "Data & ML", "ml": "Data & ML",
    "ml-models": "Data & ML", "analytics": "Data & ML",
    # Security
    "security": "Security", "compliance": "Security",
    # Finance
    "pricing": "Finance", "billing": "Finance", "legal": "Finance",
    # Social / GTM
    "marketing": "Social / GTM", "sales": "Social / GTM",
    "support": "Social / GTM", "partnerships": "Social / GTM",
    # People / Product
    "hiring": "People/Product", "roadmap": "People/Product",
}

# soft, hub-distinct colors (mirrored in the UI)
HUB_COLORS = {
    "Backend": "#7aa2ff", "Frontend": "#59c08a", "Data & ML": "#b79dff",
    "Security": "#ef8b8b", "Finance": "#e0a94a", "Social / GTM": "#f19cd0",
    "People/Product": "#5ec8d8", "General": "#9aa3b0",
}

HUBS = ["Backend", "Frontend", "Data & ML", "Security", "Finance",
        "Social / GTM", "People/Product"]


def hub_of(topic: str) -> str:
    """Map a topic (e.g. 'pricing-free-tier', 'data-platform') to its hub."""
    if not topic:
        return "General"
    parts = topic.split("-")
    for cand in [topic, parts[0], *parts]:
        if cand in HUB_OF:
            return HUB_OF[cand]
    return "General"


# coarse subcluster families — the mid level between hub and individual node.
# A granular topic ('data-platform-cdn', 'pricing-free-tier') collapses to its
# family ('data-platform', 'pricing') so each hub shows a few clear sub-blobs
# instead of dozens of singletons.
_FAMILIES = ["data-platform", "public-api", "ml-models", "tech-stack",
             "pricing", "billing", "infrastructure", "hiring", "security",
             "compliance", "marketing", "sales", "support", "partnerships",
             "frontend", "mobile", "analytics", "roadmap", "legal", "auth",
             "devops"]


def subcluster_of(topic: str) -> str:
    """Collapse a topic to its coarse subcluster family."""
    if not topic:
        return "general"
    for fam in sorted(_FAMILIES, key=len, reverse=True):
        if topic == fam or topic.startswith(fam + "-"):
            return fam
    return topic.split("-")[0]
