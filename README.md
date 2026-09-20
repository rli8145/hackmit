# Canon

**The context hub for an organization.** Canon reads the places a
team already talks — Slack, meeting transcripts, Notion, pasted notes, audio —
extracts the **decisions** buried in the noise, and keeps them in a living,
queryable **decision graph** with owners, verbatim evidence, and conflict
detection. Institutional memory that never leaves when people do.

> HackMIT 2026. See `AGENTS.md` for the project outline + build plan, and
> `canon-tracks.md` for the track strategy.

---

## Quickstart (zero dependencies)

The whole system runs on the Python 3.10+ standard library — no install needed.

```bash
python run_demo.py                 # end-to-end demo + eval numbers (offline)
python -m canon.api        # live app → http://localhost:8000
python build_static.py             # regenerate the static docs/ build
```

`run_demo.py` ingests the synthetic corpus, prints the decisions, the attention
queue Canon caught, answers a question with a citation, and reports eval
numbers. The server hosts the interactive UI: an attention queue, the decision
graph, click-through evidence, an **"ask Canon"** box, and a **paste-a-source
→ extract** box.

## The graph

The live app renders a force-directed graph of **1,003 nodes**: **68 real
decisions** (drawer-openable, with verbatim evidence and relationships — 8 from
the hand-written corpus + 60 generated) embedded in their **hub regions**, over a
**935-node synthetic backdrop** that gives Canon the shape of a mature org's
institutional memory. Colour and layout both carry the hub, so the graph reads as
named territory rather than a hairball.

The backdrop is presentation only — it is composed in `api.py::_full_graph()`
and never enters Canon, so the 68 real decisions are the ones that get
searched, scored and surfaced.

## What it catches

From the 8-source hand-written corpus Canon raises the four attention triggers
automatically (the generated decisions add more organically):

- **Superseded but unedited** — AWS→GCP and free-tier 100→50 calls; the old
  decisions still read as-is → *check they still hold*.
- **Assumption drift** — Pro pricing assumed *AWS* infra costs, which moved to
  GCP → *re-verify*.
- **Unowned** — the Pro-pricing and Q2-hiring decisions have no owner.
- **Overlap** — two live decisions on the same topic → *reconcile*.

Ask *"what's our free tier?"* and it answers **50 calls/day** (the current,
live decision — not the superseded 100), with the verbatim quote it's citing.

## Turning on the real integrations

Every model/service call sits behind an env key with an offline path, so the app
runs without any of them and lights up as you add them:

| Set this | Unlocks |
|----------|---------|
| `OPENAI_API_KEY` | LLM extraction (replaces the offline path) — **OpenAI track** |
| `DEEPGRAM_API_KEY` | raw-audio ingestion (speech-to-text) — **Deepgram track** |
| `ELEVENLABS_API_KEY` | Canon answers out loud — **ElevenLabs track** |
| `ELASTIC_URL` / `ELASTIC_API_KEY` | Elasticsearch-backed search — **Elastic track** |

Copy `.env.example` and fill in what you have. Token spend is metered per stage
from the first call (`GET /api/tokens`) for the **Token Company** track.

## Measured, not vibes

```
python -m canon.eval
```
Scores extraction precision, owner accuracy, supersession recall, conflict
recall and false edges against the seed corpus's ground-truth labels.

Offline baseline on the seed: **100% across all four, 0 false edges**. Swap in
`OPENAI_API_KEY` to measure the LLM path on harder inputs.

## Architecture

Ingest anything a team already writes → **extract** the decisions with verbatim
evidence → **relate and index** them → **surface** what needs attention and
**answer** questions about it. Each stage hands the next a `Decision`, the single
shared contract (`schema.py`, spelled out in `AGENTS.md` §5); nothing else
crosses the seams.

```
  Slack · meeting transcripts · Notion · pasted notes · audio
                             │  read-only
                             ▼
  ┌─────────────────────────────────────────────────────┐
  │ extract.py      OpenAI  ──or──  offline path        │
  │                 → Decision + verbatim evidence      │
  └─────────────────────────────────────────────────────┘
                             ▼
  ┌─────────────────────────────────────────────────────┐
  │ store.py + graph.py     relate() runs on write      │
  │   supersedes · conflicts · depends_on               │
  │   hubs.py   →  hub + subcluster on every node       │
  │   rules.json  →  the attention queue                │
  └─────────────────────────────────────────────────────┘
                             ▼
  ┌─────────────────────────────────────────────────────┐
  │ api.py (stdlib HTTP)  →  web/index.html             │
  │   /api/query  →  retrieved answer, always cited     │
  └─────────────────────────────────────────────────────┘
```

### 1. Extract — `extract.py`

One entry point, `extract(text, source_type, link, decided_on)`, with two
interchangeable paths behind the same return type:

- **OpenAI** when `OPENAI_API_KEY` is set (`gpt-4o-mini` by default, override
  with `CB_OPENAI_MODEL`). If the call raises, it falls through rather than
  failing — an API hiccup never kills the demo.
- **Offline path** otherwise, so the whole system runs and demos with no keys
  at all. Same signature, same return type, one primary decision per source.

Either way the output is a `Decision` whose evidence is quoted verbatim from the
source — the pipeline never paraphrases what someone said. Both paths meter into
`tokens.py::LEDGER`, so `GET /api/tokens` has a baseline from the very first
call.

### 2. Relate — `graph.py::relate()`, run at ingest time

Edges are computed on write, not on read. Each new decision is compared against
the **live** peers covering the same ground, and the first matching relation
wins:

| # | The new decision… | Edge |
|---|-------------------|------|
| 1 | says it is replacing something on the same ground | `supersedes`, conf 0.9 |
| 2 | asserts a rival value for the same thing | `conflicts` **both ways**, conf ≤ 0.95 |
| 3 | is simply the later call on that topic | `supersedes`, conf 0.6 |
| 4 | was decided the same day on that topic | `conflicts` both ways, conf 0.7 |

A superseded decision is never deleted — it drops to `needs_review` so the queue
can say *check it still holds*. Two conflicting decisions both stay live, and
both ends carry the edge, so either one opens onto the other in the UI. Every
edge stores a `rationale` string explaining itself.

### 3. Attention — rules are data

`rules.json` holds the severity, message and suggested action for each of the
four triggers (`live_overlap`, `superseded_unedited`, `drifted_assumption`,
`unowned`); `graph.py::compute_attention()` holds only the predicates. Adding a
trigger means adding a rule and a predicate — the left rail renders whatever the
endpoint returns, `action.label` included, so the UI never needs a change.

### 4. Hubs — `hubs.py`

Every node is tagged with a **hub** (Backend, Frontend, Data & ML, Security,
Finance, Social / GTM, People/Product) and a **subcluster** (its topic).
`api.py::_full_graph()` stamps both onto real and backdrop nodes alike via
`hub_of()` / `subcluster_of()`, so the whole payload is navigable at two
altitudes — an agent can ask for open Finance decisions without reading 1,000
nodes, and the UI uses the hub for node color, for the watermark region labels,
and for the cohesion/separation forces that keep the regions apart on screen.
The current seed spreads as roughly Backend 219 · Social / GTM 199 · Data & ML
145 · Finance 123 · People/Product 111 · Frontend 104 · Security 102.

### 5. Answer — `voice.py::answer_query()`

Answers are **retrieved, never invented** — Canon reports what is on the
record and shows the quote it read.

1. `store.py::search()` ranks every decision against the query over its
   statement plus all of its evidence, weighted toward the org's **current**
   state: a live decision outranks the one it superseded. That weighting is why
   *"what's our free tier?"* answers **50 calls/day** and not the superseded 100.
2. A candidate only counts as an answer if it genuinely shares a term with the
   question. Rank alone is not enough — something always ranks highest, and
   without this the nearest record would come back dressed as a real answer.
3. The top surviving hit is reported with its owner, status and date.
4. The citation is the decision's own stored quote, so an answer cannot exist
   without the evidence behind it.

So **"I don't have a decision on record for that" is a real answer.** Ask about
something the org never decided and Canon says so, instead of citing the
closest thing it can find — which matters more than usual for a product whose
whole claim is that you can trust what it tells you.

`speak()` (ElevenLabs) reads that answer aloud; `transcribe()` (Deepgram) feeds
the ingest side, not this one.

`search()` is the Elasticsearch swap point (Elastic track) — the one function to
replace, with the interface around it unchanged.

### 6. Serve — `api.py` + `web/index.html`

A stdlib `ThreadingHTTPServer` (no framework, no install) that loads the seed
corpus on startup and hosts the UI as a single file. The UI is one HTML
document: a canvas force-directed graph with its own spring/repulsion tick,
hub cohesion and separation forces, pixel-snapped rendering, and screen-space
label collision avoidance. It reads the JSON API and holds no state of its own.

### The static build — `build_static.py` → `docs/`

`docs/` is the zero-backend GitHub Pages copy, and it is **generated, never
edited**. `python build_static.py` bakes the graph, attention queue and every
full decision record into `docs/data.json`, then rewrites `web/index.html` into
`docs/index.html` by swapping the two-line `fetch` data layer for a client-side
one that runs search and paste-extract in the browser. It answers **identically
to the server** — the same ranking, the same grounding check, and the server's
own stopword set baked in at build time rather than restated, so the two cannot
drift apart.

**`web/index.html` is the single source of truth — edit only that, then
rebuild.** The build asserts on both splice points, so a refactor that renames
`jget`/`jpost` or the `refresh(); loop();` entrypoint fails loudly instead of
shipping a stale page.

## Structure

```
canon/
  schema.py         the Decision contract (the one shared surface)
  seed/corpus.py    8 synthetic Slack/transcript/notes sources + ground truth
  seed/synthetic.py the 60 generated real decisions
  fake_graph.py     935-node synthetic backdrop (presentation only)
  extract.py        OpenAI extraction + offline path + token metering
  tokens.py         per-stage token ledger
  store.py          the Canon: ingest, search, graph, attention
  graph.py          edge/conflict detection + attention predicates
  hubs.py           hub + subcluster tagging (the graph's named regions)
  rules.json        attention rules as data (severity, message, action)
  eval.py           scorer vs ground truth
  voice.py          Deepgram STT + ElevenLabs TTS + cited text answers
  api.py            stdlib HTTP server + JSON API + static UI host
web/index.html      single-file UI (canvas graph, attention rail, ask console)
build_static.py     generates docs/ from web/index.html — edit web/, not docs/
docs/               static GitHub Pages build (generated: index.html + data.json)
run_demo.py         narrated end-to-end demo
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
