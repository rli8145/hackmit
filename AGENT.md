# AGENTS.md — Company Brain

Guidance for coding agents (Codex, Devin, Claude Code, Warp, Cursor) and
teammates. This is the canonical agent-guidance file; `AGENT.md` is a copy —
**edit this one.**

> **HackMIT 2026 project.** This file outlines *what we're building.* The
> detailed build plan (work split, build order, conventions) comes later — see
> **§7**. For track strategy see `company-brain-tracks.md`.

---

## 1. One-liner

**Company Brain is the decision layer for an organization.** It reads the places
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

- **Primary:** Dropbox (chaos → CompanyOS), Elastic (find the signal), plus the
  official main-track entry (Dev Tools / Healthtech — *TBD, confirm the four*).
- **Value-prop fits:** Meta (team alignment), Ramp (save time & money).
- **Feature-add:** ElevenLabs + Deepgram (the voice layer).
- **Free stacks:** OpenAI + Codex, Cognition/Devin, Warp, The Token Company.

## 7. Build plan — *later*

Deferred by design. When we're ready to build, this section will hold the data
contract discipline, seed-corpus + eval strategy (so "measured better" is a real
number), build order with the demoable-slice gate, and agent conventions (run
commands, env-var names, secrets policy). Not yet.

**Team: 3 people.** The work will split across the three of us (rough shape —
pipeline/extraction · store + graph/conflict detection · UI + demo, with the
voice layer as the shared cuttable stretch). Detailed split lands here with the
rest of the build plan.

## 8. Open TODO

- [ ] **Confirm this year's four official main tracks** from the day-of app
  (`dayof.hackmit.org/prizes`) and lock the primary. Still unconfirmed.
- [ ] Write the build plan (§7) when we move from outline to implementation.

---

## Notes for agents & teammates

- **Synthetic data only in this repo.** No real company Slack/Notion content or
  workspace links (privacy + shared remote).
- The original static prototype (`kimchibrain.html`) is a client-side mock that
  contains real company data, so it is **not committed**. Ask the owner for a
  sanitized synthetic copy before adding any prototype here.
- Related: `company-brain-tracks.md` (track strategy). An earlier
  finance-reconciliation exploration is kept under `archive/maximor-recon/`.
