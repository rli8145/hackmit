# Company Brain — HackMIT 2026 Project & Track Strategy

> **One-liner:** Company Brain is the decision layer for an organization. It
> reads everywhere your team already talks — Fellow meeting transcripts, Slack,
> Notion, Docs — extracts the **decisions** buried in the noise, and keeps them
> in a living, queryable **decision graph** with owners, evidence, and conflict
> detection. Institutional memory that never leaves when people do.

---

## The problem

Every company's most important asset — *why we decided what we decided* — lives
scattered across thousands of messages, meeting transcripts, and half-finished
docs. Nobody can find it. Decisions silently contradict each other. The
assumption a call was based on quietly moves and nobody notices. When someone
leaves, the "why" leaves with them.

## What it does

- **Reads live sources, read-only:** Slack (across channels), Fellow
  transcripts, Notion, Docs. "Brain is listening everywhere."
- **Extracts decisions** from any source — a transcript, a Slack thread, or
  pasted notes — through one pipeline.
- **Builds a decision graph** with typed edges: `depends on`, `supersedes`,
  `conflicts`. Click any node for its full record.
- **Surfaces what needs attention:**
  - two live rules that cover the same ground → *update the record*
  - a newer decision changed this, the old one still reads as-is → *check it still holds*
  - the assumption underneath it has moved → *re-verify*
  - nobody is accountable → *assign an owner*
- **Every decision cites its evidence** — verbatim, from the source, with a
  link back to where it was said.

## How it works (architecture)

```
   Slack ─┐
  Fellow ─┤   ingest      ┌───────────────┐   decision graph    ┌──────────────┐
  Notion ─┼─ (read-only) ─▶  extraction    ├────────────────────▶  attention     │
    Docs ─┘                │  pipeline (LLM)│   owners · evidence │  queue + graph │
                           └───────────────┘   supersede/conflict └──────────────┘
                                   ▲                                      │
                          voice / text query ◀──────────────────────────┘
                          "ask the brain about any decision"
```

---

## Tracks we can aim for

> **Action item:** confirm this year's **four official main tracks** from the
> day-of app (`dayof.hackmit.org/prizes`) and lock the primary. The mapping
> below assumes HackMIT's recurring thematic categories.

One Company Brain submission can credibly enter **9–11 tracks**. Prioritize the
🟢 primaries; the rest are either a small feature-add or a free toolchain/write-up.

### Official main tracks (pending confirmation)

| Track | Fit | The pitch |
|-------|-----|-----------|
| **Dev Tools** 🟢 | Strong | Decision / ADR memory for engineering orgs — tracks technical decisions across Slack + Notion, flags when a newer decision supersedes an old one. |
| **Healthtech** 🟢 | Strong | Pitch as institutional memory for clinical & healthcare teams: care protocols and compliance decisions with owners + a citable audit trail. |
| **Social Good** | Medium | Org transparency & accountability — every decision has an owner, evidence, and a trail; fights institutional knowledge loss. |
| **Fintech / Education** | Reach | A decision-audit layer for finance teams, or a "school decisions brain." Reachable pivots if one of these is an official track. |

### Sponsor challenges — strong fits

- **Dropbox — "Turn digital chaos into something useful"** 🟢 *(lead here)*
  Near-bullseye. Their own example is **CompanyOS** — "an internal tool that maps
  your organization by connecting people and teams with the goals and work they
  own." Company Brain is a decision-centric CompanyOS.
- **Elastic — "Find the Signal"** 🟢
  Turn messy org comms into insights, answers, and actions. Back the decision
  store + search with **Elasticsearch** and it's a direct hit.
- **Meta — "Bringing People Closer Together with AI"** 🟢
  Meta's own prompts — *"synthesize a group discussion into plans,"* *"organize
  scattered updates into a shared story"* — are exactly what Company Brain does to
  meetings and Slack. Reframe around **team alignment & shared understanding.**
- **Ramp — "Save Time. Save Money."** 🟢
  Wide-open challenge, dead-center value prop: Company Brain saves **time**
  (find any decision + its owner in seconds instead of digging through months of
  Slack) and **money** (no costly re-litigated or silently-conflicting
  decisions, faster onboarding). No specific tech required — just frame the ROI.

### Add a small feature → unlock a track

- **ElevenLabs — voice agent** 🎙️
  Add a conversational **"ask the brain"** layer: *"What did we decide about
  pricing, and who owns it?"* → the brain answers out loud, with a citation.
  ElevenLabs rewards agentic depth, low latency, and personality — a talking
  institutional memory is a genuinely novel use case.
- **Deepgram — audio ingestion** 🎙️
  Ingest **raw meeting audio** via Deepgram speech-to-text as a source (beyond
  Fellow's pre-made transcripts). Qualifies the project and widens what the brain
  can hear. $200 free credit + a starter repo.
- **Arrowstreet — textual analysis** *(stretch)*
  Our evidence/verbatim-citation + structured extraction from corporate text maps
  to their judging criteria (evidence quality, sourced citations). Their task is
  greenwashing-specific, so this is optional.

### Stack for free — toolchain & write-up only

- **OpenAI Challenge** — power the extraction/query pipeline with the **OpenAI
  API** and use **Codex** as a dev teammate. Judged on what you build + how Codex
  helped; note one concrete way it moved you faster in the demo.
- **Cognition — "Best Use of Devin"** — build it *with* **Devin** planning,
  writing, testing, and shipping alongside you. Judged on creativity, novelty,
  polish. Perfect for an ambitious multi-integration build.
- **Warp — "Best Developer Tool"** — lean into the **Dev Tools** framing (a
  decision brain for engineering orgs) and Company Brain *is* a developer tool.
  You don't have to build *in* Warp, but using it is encouraged. Winners get
  Keychron keyboards.
- **The Token Company — LLM cost saving** — the extraction pipeline is
  LLM-heavy; show **prompt caching / cheaper models on extraction / dense
  outputs** and quantify the savings.

---

## The voice layer (why it's worth adding)

The single highest-leverage feature-add. A **conversational voice interface**:

1. **ElevenLabs** for the agent voice + real-time dialogue ("ask the brain").
2. **Deepgram** for ingesting raw meeting audio into the pipeline.

Payoff: it makes the demo *feel alive* (you talk to it on stage), and it unlocks
**two more sponsor tracks** for maybe half a day of work. A brain you can
*converse with* about your company's decisions is a memorable 2-minute demo.

---

## Suggested strategy

| Priority | Do this |
|----------|---------|
| **1** | Lock the primary: **Dropbox** (chaos→CompanyOS) as headline, **Dev Tools** or **Healthtech** as the official-track entry. |
| **2** | Add **Elasticsearch** for the decision store/search → Elastic track + better product. |
| **3** | Add the **voice layer** (ElevenLabs + Deepgram) → two tracks + demo wow. |
| **4** | Free stacks: build with **OpenAI API + Codex**, and/or **Devin**; note **Warp**; measure **Token Company** savings. |
| **5** | If time: **Meta** reframe write-up (team alignment) + **Arrowstreet** stretch. |

**Demo discipline:** one flawless 2-minute path — paste a messy Slack thread →
watch the brain extract a decision, place it in the graph, catch that it
*conflicts* with an older one, flag the missing owner, then *ask it out loud*
what the current decision is and hear it answer with a citation. Cache anything
slow; only run the crowd-pleaser live.

---

*Confirm the four official main track names and this doc gets a locked primary +
a one-paragraph tailored pitch per target track.*
