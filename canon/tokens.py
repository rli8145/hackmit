"""
Token-spend logging.  (Owner: Andrew / P1 — must exist from the first call.)

The Token Company track needs a before/after baseline you cannot retrofit, so
every model call is metered here from day one. Offline (fallback) calls log
zero tokens but still record the stage, so the ledger always reflects real
pipeline shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TokenLedger:
    # stage -> {"calls", "prompt", "completion"}
    stages: dict[str, dict[str, int]] = field(default_factory=dict)

    def log(self, stage: str, prompt: int = 0, completion: int = 0) -> None:
        s = self.stages.setdefault(stage, {"calls": 0, "prompt": 0, "completion": 0})
        s["calls"] += 1
        s["prompt"] += prompt
        s["completion"] += completion

    @property
    def total_tokens(self) -> int:
        return sum(s["prompt"] + s["completion"] for s in self.stages.values())

    def render(self) -> str:
        lines = ["token ledger:"]
        for stage, s in self.stages.items():
            lines.append(f"  {stage:<18} calls={s['calls']:<3} "
                         f"prompt={s['prompt']:<7} completion={s['completion']:<7} "
                         f"total={s['prompt'] + s['completion']}")
        lines.append(f"  {'TOTAL':<18} {self.total_tokens} tokens")
        return "\n".join(lines)


# process-wide ledger; the API and demo both read it
LEDGER = TokenLedger()
