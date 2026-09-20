"""
API server + static UI host.  (Owner: Ryan serves it, Hamid consumes it.)

Standard-library HTTP server so the whole app runs with ZERO install:

    python -m canon.api      # then open http://localhost:8000

Loads the synthetic seed corpus on startup. Endpoints:
    GET  /                      -> the web UI
    GET  /api/graph             -> decision graph (nodes + edges)
    GET  /api/attention         -> attention queue
    GET  /api/decision?id=...   -> one decision (full record)
    GET  /api/tokens            -> token ledger
    POST /api/extract           -> {text, source_type, link, date} ingest + return
    POST /api/query             -> {q} ask Canon (text answer + citation)
    POST /api/voice/ask         -> {q} same, plus base64 audio if ElevenLabs key set
"""

from __future__ import annotations

import base64
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from canon import fake_graph
from canon.hubs import hub_of, subcluster_of
from canon.extract import extract
from canon.seed.corpus import SOURCES
from canon.seed.synthetic import generate_decisions
from canon.store import Canon
from canon.tokens import LEDGER
from canon.voice import answer_query, speak

WEB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web", "index.html")
CANON = Canon()
_FAKE = fake_graph.generate(935)   # display-only backdrop, generated once


def _load_seed() -> None:
    # hand-written corpus (7) — full evidence + planted attention traps
    for s in sorted(SOURCES, key=lambda x: x.date):
        CANON.ingest(extract(s.text, s.type, s.link, s.date))
    # generated real decisions (~60) — full records, drawer-openable
    CANON.ingest(generate_decisions(60))


def _full_graph() -> dict:
    """Real decisions (interactive) embedded in the ~1000-node backdrop."""
    real = CANON.graph()
    for n in real["nodes"]:
        n["real"] = True
    nodes = real["nodes"] + _FAKE["nodes"]
    edges = real["edges"] + list(_FAKE["edges"])

    # anchor each real decision into a fake cluster that shares a topic word
    fake_by_topic: dict[str, list[str]] = {}
    for fn in _FAKE["nodes"]:
        fake_by_topic.setdefault(fn["topic"], []).append(fn["id"])
    for rn in real["nodes"]:
        words = set(rn["topic"].split("-"))
        pool = [fid for t, ids in fake_by_topic.items()
                if words & set(t.split("-")) for fid in ids]
        pool = pool or [fn["id"] for fn in _FAKE["nodes"][:50]]
        for fid in pool[:1]:
            edges.append({"source": rn["id"], "type": "depends_on", "target": fid})

    # tag every node with its hub + subcluster (agent- and human-navigable)
    for n in nodes:
        n["hub"] = hub_of(n.get("topic", ""))
        n["subcluster"] = subcluster_of(n.get("topic", ""))
    return {"nodes": nodes, "edges": edges}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):  # quiet
        pass

    # -- helpers -----------------------------------------------------------
    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict | None:
        """Parse the JSON request body, or return None if it is unusable.

        Returning None (rather than raising) lets do_POST answer 400. An
        uncaught exception here escapes BaseHTTPRequestHandler and drops the
        connection with no response at all, which the browser sees as a
        fetch that never resolves.
        """
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except (TypeError, ValueError):
            return None
        if n <= 0:
            return {}
        try:
            parsed = json.loads(self.rfile.read(n) or b"{}")
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return None
        # A bare list/str/number is valid JSON but every caller below does
        # .get() on this, so treat anything but an object as a bad request.
        return parsed if isinstance(parsed, dict) else None

    # -- routes ------------------------------------------------------------
    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            with open(WEB, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif path == "/api/graph":
            self._json(_full_graph())
        elif path == "/api/attention":
            self._json(CANON.attention())
        elif path == "/api/decision":
            from urllib.parse import parse_qs, urlparse
            did = parse_qs(urlparse(self.path).query).get("id", [""])[0]
            d = CANON.get(did)
            self._json(d.to_dict() if d else {"error": "not found"},
                       200 if d else 404)
        elif path == "/api/tokens":
            self._json({"stages": LEDGER.stages, "total": LEDGER.total_tokens})
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        path = self.path.split("?")[0]
        # Read the body exactly once, before dispatch: rfile cannot be
        # re-read, and an unread body desyncs a keep-alive connection.
        b = self._body()
        if b is None:
            self._json({"error": "request body must be a JSON object"}, 400)
            return
        if path == "/api/extract":
            new = extract(b.get("text", ""), b.get("source_type", "paste"),
                          b.get("link", "paste://ui"), b.get("date", "2026-03-15"))
            CANON.ingest(new)
            self._json({"extracted": [d.to_dict() for d in new],
                        "attention": CANON.attention()})
        elif path == "/api/query":
            self._json(answer_query(CANON, b.get("q", "")))
        elif path == "/api/voice/ask":
            res = answer_query(CANON, b.get("q", ""))
            audio = speak(res["answer"]) if res.get("answer") else None
            if audio:
                res["audio_b64"] = base64.b64encode(audio).decode()
            self._json(res)
        else:
            self._json({"error": "not found"}, 404)


def main():
    _load_seed()
    port = int(os.environ.get("PORT", 8000))
    print(f"Canon on http://localhost:{port}  "
          f"({len(CANON.decisions)} decisions, "
          f"{len(CANON.attention())} attention items)")
    ThreadingHTTPServer(("", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
