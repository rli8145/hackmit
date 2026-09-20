"""
Build a static version of Company Brain for GitHub Pages.

Bakes the full graph (real decisions embedded in the ~1000-node backdrop),
the attention queue, and the real decision records into docs/data.json. The
static docs/index.html runs search + paste-extract client-side, so the hosted
site is fully interactive with no backend.

    python build_static.py
"""

from __future__ import annotations

import json
import os

from company_brain import api  # sets up BRAIN + fake backdrop at import

api._load_seed()  # ingest the 7 seed + ~60 generated real decisions

data = {
    "graph": api._full_graph(),
    "attention": api.BRAIN.attention(),
    "decisions": {d.id: d.to_dict() for d in api.BRAIN.decisions},
}

out = os.path.join(os.path.dirname(__file__), "docs", "data.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w") as f:
    json.dump(data, f)

g = data["graph"]
print(f"wrote {out}")
print(f"  graph: {len(g['nodes'])} nodes / {len(g['edges'])} edges "
      f"({sum(1 for n in g['nodes'] if n.get('real'))} real)")
print(f"  attention: {len(data['attention'])} items")
print(f"  decision records: {len(data['decisions'])}")
