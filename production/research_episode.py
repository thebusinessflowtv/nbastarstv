from __future__ import annotations

import json
from typing import Any

from production import research_episode_business_base as core


def build_prompt(topic: dict[str, Any]) -> str:
    return f"""
You are the low-cost research desk for NBA Stars, an English-language YouTube channel focused on NBA players, teams, rivalries, records, rules, curiosities, rise-and-fall stories and unusual basketball history.

TOPIC SEED
{json.dumps(topic, ensure_ascii=False)}

STRICT COST / OUTPUT RULES
- Perform AT MOST ONE web search total. Never perform a second search.
- Do not narrate your process before or after searching.
- Make the one search broad and information-dense.
- Prioritize NBA.com, official team/player sources, Basketball-Reference/Stathead-style historical records when accessible, AP/Reuters, ESPN and other established sports reporting.
- After the search, call {core.RESEARCH_TOOL_NAME} immediately and exactly once.
- Keep the tool payload compact: thesis <= 60 words; exactly 6 factual claims, each <= 32 words; exactly 4 sources; at most 4 verified numbers; at most 4 timeline entries; at most 2 short risk flags.
- The `sources` array MUST contain exactly four distinct HTTP(S) URLs.
- Every facts[].source_url, verified_numbers[].source_url and timeline[].source_url MUST match one of those four sources[].url values.

NBA RESEARCH RULES
- Treat the seed angle as a hypothesis, not a fact.
- Distinguish regular-season, playoff, career and single-game statistics.
- For records, trades, contracts, injuries, suspensions, bans, disputes and quotes, require direct support from the cited source.
- Current rumors must be labeled as rumors and used only when reported by a reputable named source; never convert a rumor into a fact.
- Do not infer motives, medical conditions, criminality or private facts.
- Historical claims must identify the relevant era/date when necessary.
- Mark safe_for_packaging=true only when the cited source directly supports title/thumbnail/hook use.
- If a dramatic claim cannot be supported within the single-search budget, omit it rather than spending another search.
""".strip()


core.RESEARCH_TOOL["description"] = "Submit a compact, source-backed research brief for one NBA storytelling documentary."
core.build_prompt = build_prompt


if __name__ == "__main__":
    core.main()
