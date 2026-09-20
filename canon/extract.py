"""
Extraction pipeline.  (Owner: Andrew / P1.)

Turns a raw source (Slack thread, transcript, notes, audio transcript) into
`Decision` objects with VERBATIM evidence.

Two paths, same return type:
  - OpenAI  (real, required for the OpenAI track): set OPENAI_API_KEY. The API
    powers the extraction; Codex is our dev teammate building around it.
  - fallback (deterministic, offline): rule-based so the whole system runs and
    demos without any keys. Extracts one primary decision per source.

Every call meters tokens into canon.tokens.LEDGER.
"""

from __future__ import annotations

import json
import os
import re

from canon.schema import Decision, Evidence, Source
from canon.tokens import LEDGER

# CB_OPENAI_MODEL is the pre-rename name — still honoured so a teammate's
# existing .env keeps working.
MODEL = (os.environ.get("CANON_OPENAI_MODEL")
         or os.environ.get("CB_OPENAI_MODEL") or "gpt-4o-mini")

DECISION_CUES = (
    "decided", "decision:", "we'll", "we're going with", "going with",
    "standardize on", "we are going with", "changing the free tier",
    "we should", "let's go with",
)

_TOPIC_KEYWORDS = [
    ("infrastructure", ("aws", "gcp", "infra", "migrat", "region", "us-east")),
    ("pricing-pro", ("pro at", "pro plan", "$49", "price pro")),
    ("pricing-free-tier", ("free tier", "calls/day", "api calls")),
    ("hiring", ("hire", "hiring", "engineer", "headcount")),
    ("tech-stack", ("python", "standardize", "typescript", "framework")),
]

_UNOWNED_MARKERS = ("nobody", "no one", "tbd", "unassigned", "nobody's assigned",
                    "nobody grabbed", "owner: tbd", "no owner")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract(text: str, source_type: str, link: str, decided_on: str,
            use_llm: bool | None = None) -> list[Decision]:
    """Extract decisions from one source. Auto-selects OpenAI vs fallback."""
    if use_llm is None:
        use_llm = bool(os.environ.get("OPENAI_API_KEY"))
    if use_llm:
        try:
            return _extract_llm(text, source_type, link, decided_on)
        except Exception as e:  # never let the demo die on an API hiccup
            print(f"[extract] OpenAI path failed ({e}); using fallback")
    return _extract_fallback(text, source_type, link, decided_on)


# ---------------------------------------------------------------------------
# OpenAI path
# ---------------------------------------------------------------------------

_SYSTEM = (
    "You extract DECISIONS from workplace text (Slack, meeting transcripts, "
    "notes). A decision is a concrete choice the team committed to. For each, "
    "return: statement (one sentence), owner (person accountable, or null if "
    "nobody is), decided_on (echo the given date), topic (a short kebab-case "
    "tag so related decisions group together), assumptions (list of things it "
    "rests on), and evidence (a list of VERBATIM quotes copied exactly from the "
    "text). Never invent quotes. Return JSON: {\"decisions\": [...]}."
)


def _extract_llm(text, source_type, link, decided_on) -> list[Decision]:
    from openai import OpenAI  # lazy import
    client = OpenAI()
    prompt = (f"Date of this source: {decided_on}\nSource type: {source_type}\n"
              f"---\n{text}\n---")
    resp = client.chat.completions.create(
        model=MODEL,
        response_format={"type": "json_object"},
        messages=[{"role": "system", "content": _SYSTEM},
                  {"role": "user", "content": prompt}],
    )
    if resp.usage:
        LEDGER.log("extract:openai", resp.usage.prompt_tokens,
                   resp.usage.completion_tokens)
    data = json.loads(resp.choices[0].message.content)
    out: list[Decision] = []
    for i, d in enumerate(data.get("decisions", [])):
        raw_owner = d.get("owner")
        owner = raw_owner.lower().strip() if isinstance(raw_owner, str) and raw_owner.strip() else None
        out.append(Decision(
            id=_mk_id(link, i),
            statement=d.get("statement", "").strip(),
            owner=owner,
            decided_on=decided_on,
            source=Source(type=source_type, link=link),
            evidence=[Evidence(verbatim_quote=q, link=link)
                      for q in d.get("evidence", []) if q],
            assumptions=[a for a in d.get("assumptions", []) if a],
            topic=d.get("topic", "") or _infer_topic(d.get("statement", "")),
        ))
    return out


# ---------------------------------------------------------------------------
# Fallback path (deterministic, offline)
# ---------------------------------------------------------------------------

def _extract_fallback(text, source_type, link, decided_on) -> list[Decision]:
    LEDGER.log("extract:fallback")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    decision_lines = [ln for ln in lines if _is_decision_line(ln)]
    if not decision_lines:
        return []

    # one primary decision per source: the most informative decision line
    best = max(decision_lines, key=_informativeness)
    statement = _clean_statement(best)
    evidence = [Evidence(verbatim_quote=ln, link=link) for ln in decision_lines]

    return [Decision(
        id=_mk_id(link, 0),
        statement=statement,
        owner=_find_owner(lines),
        decided_on=decided_on,
        source=Source(type=source_type, link=link),
        evidence=evidence,
        assumptions=_find_assumptions(lines),
        topic=_infer_topic(text),
    )]


def _is_decision_line(line: str) -> bool:
    low = line.lower()
    return any(cue in low for cue in DECISION_CUES)


def _informativeness(line: str) -> int:
    # prefer lines with concrete nouns/numbers over vague "decided then"
    s = _clean_statement(line)
    score = len(s)
    if re.search(r"\d", s):
        score += 20
    if any(kw in s.lower() for _, kws in _TOPIC_KEYWORDS for kw in kws):
        score += 20
    return score


def _sentence_score(s: str) -> int:
    score = len(s)
    if re.search(r"\d", s):
        score += 25
    if any(kw in s.lower() for _, kws in _TOPIC_KEYWORDS for kw in kws):
        score += 25
    return score


def _clean_statement(line: str) -> str:
    s = re.sub(r"^\s*[A-Za-z][\w'-]*:\s*", "", line)      # drop "name: "
    s = re.sub(r"(?i)\bdecision:\s*", "", s)
    s = re.sub(r"(?i)^\s*-\s*", "", s)
    s = re.sub(r"(?i)\bwe (decided|are going|'re going) (to|that|with)?\s*", "", s)
    s = re.sub(r"(?i)\bwe decided\b\s*", "", s)
    s = re.sub(r"(?i)\bwe'll\b\s*", "", s)
    s = re.sub(r"(?i)\bgoing with\b", "use", s)
    s = re.sub(r"(?i)\bwe're\b\s*", "", s)
    # keep only the most decision-bearing sentence (drop chatty preamble)
    parts = [p.strip(" .") for p in re.split(r"\.\s+", s) if p.strip(" .")]
    if len(parts) > 1:
        s = max(parts, key=_sentence_score)
    s = re.sub(r"(?i)^(yes|yeah|ok|okay|so|well|right|sure)\b[\s,—-]*", "", s)
    s = s.strip(" .")
    return s[:1].upper() + s[1:] if s else s


def _find_owner(lines: list[str]) -> str | None:
    joined = " ".join(lines).lower()
    for ln in lines:
        low = ln.lower()
        if "i'll own" in low or "i own" in low or "i will own" in low:
            m = re.match(r"\s*([A-Za-z][\w'-]*)\s*:", ln)
            if m:
                return m.group(1).lower()
    m = re.search(r"(?i)owner:\s*([A-Za-z][\w'-]*)", joined)
    if m and m.group(1).lower() not in ("tbd", "none", "nobody"):
        return m.group(1).lower()
    if any(mk in joined for mk in _UNOWNED_MARKERS):
        return None
    return None


def _find_assumptions(lines: list[str]) -> list[str]:
    out = []
    for ln in lines:
        if re.search(r"(?i)\bassum(e|es|ing|ption)\b", ln):
            out.append(_clean_statement(ln))
    return out


def _infer_topic(text: str) -> str:
    low = text.lower()
    best, best_hits = "general", 0
    for topic, kws in _TOPIC_KEYWORDS:
        hits = sum(1 for kw in kws if kw in low)
        if hits > best_hits:                      # ties keep the earlier topic
            best, best_hits = topic, hits
    return best


def _mk_id(link: str, idx: int) -> str:
    tail = re.sub(r"\W+", "-", link).strip("-")[-24:]
    return f"DEC-{tail}-{idx}"
