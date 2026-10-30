#!/usr/bin/env python3
"""check-agent-originality.py — flag agents that substantially duplicate another.

Borrowed pattern from the agency-agents corpus (msitarzewski/agency-agents, MIT):
compare each agent's body against the whole roster using entity-neutralized
N-word shingle overlap, so a find-and-replace "re-skin" (swap the agent name /
department / client) cannot hide a copy.

Why it matters for SAMRUDHI: the Digital Workforce has 194 distinct roles. A
contributor who re-skins an existing agent (new name, same method) bloats the
registry with a duplicate that is well-formed and mergeable — easy to miss in
review. This check surfaces it.

Usage:
    python scripts/check-agent-originality.py            # audit all 194
    python scripts/check-agent-originality.py SAM-AG-082 # check one agent

Tunables (env):
    ORIGINALITY_FAIL  default 40  — at/above this %, treated as a duplicate
    ORIGINALITY_WARN  default 20  — at/above this %, surfaced as a warning

Exit status: 0 = all below FAIL; 1 = at least one at/above FAIL.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents.registry import AGENTS  # noqa: E402

FAIL = float(os.environ.get("ORIGINALITY_FAIL", "40"))
WARN = float(os.environ.get("ORIGINALITY_WARN", "20"))
N = 8  # shingle size (words)

# Proper nouns / identifiers to neutralize so a name-swap can't hide a copy.
_NEUTRALIZE = re.compile(
    r"(SAM-AG-\d+|[A-Z][a-z]+(?:\s[A-Z][a-z]+)*|\b(?:SAMRUDHI|SAM)\b)"
)


def shingles(text: str, n: int = N) -> set[str]:
    text = _NEUTRALIZE.sub(" X ", text.lower())
    words = re.findall(r"[a-z0-9]+", text)
    if len(words) < n:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i:i + n]) for i in range(len(words) - n + 1)}


def similarity(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return 100.0 * len(a & b) / len(a | b)


def main() -> None:
    only = sys.argv[1] if len(sys.argv) > 1 else None
    agents = [a for a in AGENTS if (only is None or a.id == only)]
    corpus = {a.id: shingles(a.system_prompt) for a in AGENTS}

    worst = 0.0
    flagged = []
    for a in agents:
        mine = corpus[a.id]
        for other_id, other in corpus.items():
            if other_id == a.id:
                continue
            s = similarity(mine, other)
            worst = max(worst, s)
            if s >= WARN:
                flagged.append((s, a.id, other_id))

    flagged.sort(reverse=True)
    for s, x, y in flagged[:20]:
        tag = "FAIL" if s >= FAIL else "warn"
        print(f"[{tag}] {x} ~ {y}: {s:.1f}%")

    print(f"\nchecked {len(agents)} agent(s); worst pairwise similarity "
          f"{worst:.2f}% (warn>={WARN:.0f}%, fail>={FAIL:.0f}%)")
    if any(s >= FAIL for s, _, _ in flagged):
        print("RESULT: DUPLICATE(S) DETECTED — review the FAIL lines above.")
        sys.exit(1)
    print("RESULT: OK — no agent exceeds the duplicate threshold.")


if __name__ == "__main__":
    main()