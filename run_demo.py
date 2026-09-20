"""
Canon — end-to-end demo (offline, zero deps).

    python run_demo.py

Ingests the synthetic corpus, shows the decision graph and the attention queue
Canon caught, asks it a question (answered with a citation), and prints the
eval numbers + token ledger. This is the narrated version of the live demo.
"""

from __future__ import annotations

import os
import sys

# Windows consoles default to a legacy codepage (cp1252/cp437) that can't
# encode the box-drawing/emoji characters below and crashes with
# UnicodeEncodeError before anything prints. Force UTF-8 output when possible.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

from canon.eval import run_eval
from canon.tokens import LEDGER
from canon.voice import answer_query

SEP = "─" * 58


def main():
    mode = "OpenAI API" if os.environ.get("OPENAI_API_KEY") else "fallback (offline, no key)"
    print(f"\nCanon — extraction mode: {mode}\n{SEP}")

    res, canon = run_eval()

    print("DECISIONS ON RECORD")
    for d in canon.decisions:
        tag = {"live": "●", "needs_review": "⚠", "superseded": "×"}.get(d.status, "·")
        owner = d.owner or "UNOWNED"
        print(f"  {tag} [{d.status:<12}] {owner:<7} {d.statement[:52]}")

    print(f"\n{SEP}\nNEEDS ATTENTION (what Canon caught)")
    for a in canon.attention():
        print(f"  ⚑ {a['type']:<16} {a['message']}")

    print(f"\n{SEP}\nASK CANON")
    for q in ["What is our free tier?", "Where do we host our infrastructure?"]:
        r = answer_query(canon, q)
        print(f"  Q: {q}")
        print(f"  A: {r['answer']}")
        if r.get("citation"):
            print(f"     └ cited: \"{r['citation'][:70]}\"")
        print()

    print(SEP)
    print(res.render())
    print(f"\n{LEDGER.render()}")
    print(f"\n{SEP}\nRun the live app:  python -m canon.api  →  http://localhost:8000\n")


if __name__ == "__main__":
    main()
