"""
Company Brain — end-to-end demo (offline, zero deps).

    python run_demo.py

Ingests the synthetic corpus, shows the decision graph and the attention queue
the brain caught, asks it a question (answered with a citation), and prints the
eval numbers + token ledger. This is the narrated version of the live demo.
"""

from __future__ import annotations

import os

from company_brain.eval import run_eval
from company_brain.tokens import LEDGER
from company_brain.voice import answer_query

SEP = "─" * 58


def main():
    mode = "OpenAI API" if os.environ.get("OPENAI_API_KEY") else "fallback (offline, no key)"
    print(f"\nCompany Brain — extraction mode: {mode}\n{SEP}")

    res, brain = run_eval()

    print("DECISIONS ON RECORD")
    for d in brain.decisions:
        tag = {"live": "●", "needs_review": "⚠", "superseded": "×"}.get(d.status, "·")
        owner = d.owner or "UNOWNED"
        print(f"  {tag} [{d.status:<12}] {owner:<7} {d.statement[:52]}")

    print(f"\n{SEP}\nNEEDS ATTENTION (what the brain caught)")
    for a in brain.attention():
        print(f"  ⚑ {a['type']:<16} {a['message']}")

    print(f"\n{SEP}\nASK THE BRAIN")
    for q in ["What is our free tier?", "Where do we host our infrastructure?"]:
        r = answer_query(brain, q)
        print(f"  Q: {q}")
        print(f"  A: {r['answer']}")
        if r.get("citation"):
            print(f"     └ cited: \"{r['citation'][:70]}\"")
        print()

    print(SEP)
    print(res.render())
    print(f"\n{LEDGER.render()}")
    print(f"\n{SEP}\nRun the live app:  python -m company_brain.api  →  http://localhost:8000\n")


if __name__ == "__main__":
    main()
