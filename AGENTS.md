# AGENTS.md — Company Brain

Guidance for coding agents (Codex, Devin, Claude Code, Warp, Cursor) and
teammates. This is the canonical agent-guidance file; `AGENT.md` is a copy —
**edit this one.**

> **HackMIT 2026 project.** §1–6 outline *what we're building*; §7 is the
> 3-person build plan. For track strategy see `company-brain-tracks.md`.

---

## 1. One-liner

**Company Brain is the context hub for an organization.** It reads the places
a team already talks — Slack, meeting transcripts, Notion, pasted notes, audio —
extracts the **decisions** buried in the noise, and keeps them in a living,
queryable **decision graph** with owners, evidence, and conflict detection.
Institutional memory that never leaves when people do.

## 2. The problem

A company's most valuable asset — *why we decided what we decided* — lives
scattered across thousands of messages, transcripts, and half-finished docs.

- Nobody can find it.
- Decisions silently **contradict** each other.
- The **assumption** a call rested on quietly moves, and nobody notices.
- No one is clearly **accountable** for a given decision.
- When someone leaves, the "why" leaves with them.

## 3. What it does

- **Reads live sources, read-only** — Slack (across channels), meeting
  transcripts, Notion, Docs. "Listening everywhere."
- **Extracts decisions** from any source — a transcript, a Slack thread, or
  pasted notes — through one pipeline.
- **Builds a decision graph** with typed edges: `depends_on`, `supersedes`,
  `conflicts`. Click any node for its full record.
- **Surfaces what needs attention:**
  - two live decisions cover the same ground → *update the record*
  - a newer decision changed this; the old one still reads as-is → *check it holds*
  - the assumption underneath it has moved → *re-verify*
  - nobody is accountable → *assign an owner*
- **Cites its evidence** — verbatim, from the source, with a link back to where
  it was said.
- **Answers questions** about any decision, by **text and voice**, always with a
  citation.

## 4. How it works (concept)

```
  Slack ─┐
  Txpts ─┤   ingest      ┌──────────────┐   decision graph      ┌──────────────┐
  Notion ┼─ (read-only) ─▶  extraction   ├──────────────────────▶  attention     │
  Notes ─┤               │  (decisions + │   owners · evidence   │  queue + graph │
  Audio ─┘               │   evidence)   │   supersede/conflict  └──────┬────────┘
                         └──────────────┘                               │
                          query (text / voice), answered with citation ◀┘
```

Four stages: **ingest** any source → **extract** decisions with verbatim
evidence → **store & relate** them (detect supersessions and conflicts against
what's already live) → **surface & answer** (attention queue, graph, and
cited Q&A by text or voice).

## 5. The decision (core object)

The whole product revolves around one shape:

```jsonc
Decision {
  id,
  statement,                               // the decision, one sentence
  status: "live" | "superseded" | "needs_review",
  owner,                                   // null = unowned  → attention
  decided_on,                              // ISO date
  source: { type, link },                  // slack | fellow | notion | paste | audio
  evidence: [ { verbatim_quote, link } ],  // why we believe it
  assumptions: [ ... ],                    // what it rests on
  edges: [ { type, target_id } ]           // depends_on | supersedes | conflicts
}
```

**Attention rules are data, not hardcoded UI:** live-vs-live overlap,
superseded-but-unedited, drifted assumption, unowned.

## 6. Tracks we're targeting

Full strategy in `company-brain-tracks.md`. In short, one submission credibly
enters **9–11 tracks**:

- **Primary:** Dropbox (chaos → CompanyOS), Elastic (find the signal), plus an
  official main-track entry (Dev Tools / Healthtech).
- **Value-prop fits:** Meta (team alignment), Ramp (save time & money).
- **Feature-add:** ElevenLabs + Deepgram (the voice layer).
- **Free stacks:** OpenAI + Codex, Cognition/Devin, Warp, The Token Company.

## 7. Build plan (3 people)

> **The gate is the load-bearing checkpoint — everything after it is bonus.**

### The core object is already defined — see §5

That `Decision` shape is the data contract. Build against small **fixture
JSONs** that follow it so nobody is blocked on another part (the trick that
unblocked parallelism on the recon scaffold).

### Split

- **Andrew — P1 · Pipeline.** Ingest adapters (paste / Slack thread /
  transcript) + **OpenAI** extraction → `Decision` objects. **Owns the data
  contract and the synthetic seed corpus** (he's generating the test input
  anyway, and owns the prototype/source context). Also owns **token-spend
  logging** — a thin wrapper on the OpenAI client that must exist from the
  *first* call (The Token Company needs a baseline you can't retrofit).
- **Ryan — P2 · Store + graph.** Storage, **edge/conflict detection**, attention
  rules as data, and the thin API the UI calls. Owns the **eval scorer** — keep
  it to ~6 synthetic threads / ~15 labeled decisions: extraction precision +
  conflict-detection hit rate. A number for the demo, not a benchmark.
- **Hamid — P3 · UI + demo.** First task: **sanitize the prototype** — strip the
  `Inference Health` title, replace the `SEED_*` arrays and real Slack/Notion
  links with synthetic data. That makes the UI committable *and* is the natural
  first step of wiring it to P2's (Ryan's) API — the seams are exactly where the
  seed arrays were. Owns the **demo script** from Phase 3 onward.

> Andrew↔Ryan (P1↔P2) can swap if that fits your strengths better; Hamid on
> P3 is fixed. **Ownership boundary to avoid overlap:** Andrew stops at emitting
> `Decision` objects to Ryan's API; Ryan owns everything about how they're
> stored/related; Hamid consumes Ryan's API and never reaches into the pipeline.
> The `Decision` contract (§5) is the only shared surface — change it only by
> agreement.

### Order (phases, with the gate)

| Phase | Andrew (P1 · Pipeline) | Ryan (P2 · Store + graph) | Hamid (P3 · UI + demo) |
|-------|------------------------|--------------------------|------------------------|
| **1 · Setup** | data contract + fixture JSONs | agree on API shape | wire UI to static fixtures |
| **2 · Core** | extraction end-to-end on one thread | store + API skeleton | prototype sanitized |
| **3 · Integrate** | more sources / robustness | conflict/edge detection + attention queue | UI wired to live API |
| **⛔ THE GATE** | **demoable slice:** paste thread → decision extracted → placed in graph → **conflict caught** → **missing owner flagged** | | |
| **4 · After the gate** | voice (cuttable) | eval numbers | polish |
| **5 · Final** | pre-ingest corpus; cache everything; **only the final paste runs live** | | rehearse |

### Hard requirements, with cut priorities

Three people can't protect everything — so each track requirement has a cut line:

1. **OpenAI API in extraction** — free, it *is* the pipeline. **Never cut.**
2. **Elasticsearch** — the **riskiest dependency.** Give it one focused attempt;
   if it fights you, fall back to **SQLite / in-memory + embedding similarity**
   and drop the Elastic track. Don't sink the night into it out of loyalty.
3. **Voice** — only *after* the gate. The halves are independent: **Deepgram**
   STT ingest unlocks Deepgram's track alone; **ElevenLabs** spoken answers
   unlocks theirs alone. If squeezed, ship one half.
4. **Codex / Devin / Warp** — zero build cost, but each needs an anecdote. All
   three people jot one concrete "Codex/Devin did X" moment **as they go**;
   retrofitting Sunday morning produces generic filler.

### Conventions

- **Secrets — never commit.** Read keys from env; keep a `.env.example`:
  `OPENAI_API_KEY`, `DEEPGRAM_API_KEY`, `ELEVENLABS_API_KEY`,
  `ELASTIC_URL` / `ELASTIC_API_KEY`.
- **Synthetic data only** in this repo (see notes below).
- **Seed data** lives in `company_brain/seed/`. **The demo path is sacred** — no
  refactors the night before judging.
- **Run commands:** `python run_demo.py` (offline end-to-end + eval);
  `python -m company_brain.api` (live UI at http://localhost:8000).

## 8. Status & open TODO

**A working end-to-end implementation now exists** (see `README.md`): stdlib
server + UI, extraction (OpenAI + offline fallback), decision graph, all four
attention rules, cited text/voice answers, eval at 100% on the seed, token
metering. Real integrations activate behind env keys (`.env.example`).

Remaining:
- [ ] Add real API keys and validate the OpenAI / Deepgram / ElevenLabs /
  Elastic paths (all wired, untested without keys).
- [ ] Harder eval inputs to stress the LLM extraction path beyond the seed.
- [ ] Polish the UI graph view (currently topic-grouped cards, not a node graph).

---

## Notes for agents & teammates

- **Synthetic data only in this repo.** No real company Slack/Notion content or
  workspace links (privacy + shared remote).
- The original static prototype (`kimchibrain.html`) is a client-side mock that
  contains real company data, so it is **not committed**. Ask the owner for a
  sanitized synthetic copy before adding any prototype here.
- Related: `company-brain-tracks.md` (track strategy). An earlier
  finance-reconciliation exploration is kept under `archive/maximor-recon/`.
