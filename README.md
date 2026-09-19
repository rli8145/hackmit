# Company Brain

**The decision layer for an organization.** Company Brain reads the places a
team already talks — Slack, meeting transcripts, Notion, pasted notes, audio —
extracts the **decisions** buried in the noise, and keeps them in a living,
queryable **decision graph** with owners, verbatim evidence, and conflict
detection. Institutional memory that never leaves when people do.

> HackMIT 2026. See `AGENTS.md` for the project outline + build plan, and
> `company-brain-tracks.md` for the track strategy.

---

## Quickstart (zero dependencies)

The whole system runs on the Python 3.10+ standard library — no install needed.

```bash
python run_demo.py                 # end-to-end demo + eval numbers (offline)
python -m company_brain.api        # live app → http://localhost:8000
```

`run_demo.py` ingests the synthetic corpus, prints the decisions, the attention
queue the brain caught, answers a question with a citation, and reports eval
numbers. The server hosts the interactive UI: an attention queue, the decision
graph, click-through evidence, an **"ask the brain"** box, and a **paste-a-source
→ extract** box.

## What it catches

From 7 synthetic sources the brain builds 7 decisions and raises the four
attention triggers automatically:

- **Superseded but unedited** — AWS→GCP and free-tier 100→50 calls; the old
  decisions still read as-is → *check they still hold*.
- **Assumption drift** — Pro pricing assumed *AWS* infra costs, which moved to
  GCP → *re-verify*.
- **Unowned** — the Pro-pricing and Q2-hiring decisions have no owner.
- **Overlap** — two live decisions on the same topic → *reconcile*.

Ask *"what's our free tier?"* and it answers **50 calls/day** (the current,
live decision — not the superseded 100), with the verbatim quote it's citing.

## Turning on the real integrations

Every model/service call is behind an env key with an offline fallback, so the
app runs without any of them and lights up as you add them:

| Set this | Unlocks |
|----------|---------|
| `OPENAI_API_KEY` | LLM extraction (replaces the rule-based fallback) — **OpenAI track** |
| `DEEPGRAM_API_KEY` | raw-audio ingestion (speech-to-text) — **Deepgram track** |
| `ELEVENLABS_API_KEY` | the brain answers out loud — **ElevenLabs track** |
| `ELASTIC_URL` / `ELASTIC_API_KEY` | Elasticsearch-backed search — **Elastic track** |

Copy `.env.example` and fill in what you have. Token spend is metered per stage
from the first call (`GET /api/tokens`) for the **Token Company** track.

## Measured, not vibes

```
python -m company_brain.eval
```
Scores extraction precision, owner accuracy, and supersession recall against the
seed corpus's ground-truth labels. Offline fallback baseline: **100% / 100% /
100%** on the seed (the corpus is designed to be fully solvable; swap in
`OPENAI_API_KEY` to measure the LLM path on harder inputs).

## Structure

```
company_brain/
  schema.py        the Decision contract (the one shared surface)
  seed/corpus.py   synthetic Slack/transcript/notes + ground truth
  extract.py       OpenAI extraction + offline fallback + token metering
  tokens.py        per-stage token ledger
  store.py         the Brain: ingest, search, graph, attention
  graph.py         edge/conflict detection + attention rules
  eval.py          scorer vs ground truth
  voice.py         Deepgram STT + ElevenLabs TTS + cited text answers
  api.py           stdlib HTTP server + JSON API
web/index.html     single-file UI
run_demo.py        narrated end-to-end demo
```

## API

```
GET  /api/graph            nodes + edges
GET  /api/attention        the attention queue
GET  /api/decision?id=…    one full record (statement, owner, evidence, edges)
GET  /api/tokens           token ledger
POST /api/extract          {text, source_type, link, date} → ingest + return
POST /api/query            {q} → cited text answer
POST /api/voice/ask        {q} → answer + base64 MP3 (if ElevenLabs key set)
```
