"""
Voice layer.  (Owner: shared / cuttable — AGENTS.md §7.)

Two independent halves, each unlocking its own track:
  - transcribe()  Deepgram STT — ingest raw meeting audio into the pipeline
  - speak()       ElevenLabs TTS — the brain answers out loud

Both are behind API keys; offline they no-op so the rest of the system runs.
The text answer (`answer_query`) always works — voice is additive.
"""

from __future__ import annotations

import os

from company_brain.store import Brain


def transcribe(audio_bytes: bytes) -> str | None:
    """Deepgram speech-to-text. Returns None if no key (offline)."""
    key = os.environ.get("DEEPGRAM_API_KEY")
    if not key:
        return None
    from deepgram import DeepgramClient, PrerecordedOptions  # lazy
    dg = DeepgramClient(key)
    resp = dg.listen.rest.v("1").transcribe_file(
        {"buffer": audio_bytes},
        PrerecordedOptions(model="nova-2", smart_format=True),
    )
    return resp.results.channels[0].alternatives[0].transcript


def speak(text: str) -> bytes | None:
    """ElevenLabs text-to-speech. Returns MP3 bytes, or None if no key."""
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        return None
    from elevenlabs.client import ElevenLabs  # lazy
    client = ElevenLabs(api_key=key)
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "Rachel")
    audio = client.text_to_speech.convert(
        voice_id=voice_id, model_id="eleven_turbo_v2",
        text=text, output_format="mp3_44100_128")
    return b"".join(audio)


def answer_query(brain: Brain, query: str) -> dict:
    """Answer a question about the org's decisions, with a citation.

    Always available (no key needed). Returns the current (live-preferred)
    decision plus its verbatim evidence — the brain never answers uncited.
    """
    results = brain.search(query, k=3)
    if not results or results[0][1] <= 0:
        return {"answer": "I don't have a decision on record for that.",
                "decision": None, "citation": None}
    top, score = results[0]
    owner = top.owner or "nobody yet"
    status = {"live": "current", "needs_review": "flagged (a newer decision may "
              "have changed it)", "superseded": "superseded"}.get(top.status, top.status)
    answer = (f"The {status} decision is: {top.statement} "
              f"Owner: {owner}. Decided {top.decided_on}.")
    citation = top.evidence[0].verbatim_quote if top.evidence else None
    return {"answer": answer, "decision": top.to_dict(),
            "citation": citation, "score": score}
