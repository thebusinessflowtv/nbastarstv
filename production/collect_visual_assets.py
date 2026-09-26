from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from production import collect_visual_assets_hq as core

ROOT = Path(__file__).resolve().parents[1]


def arg_value(name: str) -> str:
    try:
        i = sys.argv.index(name)
        return sys.argv[i + 1]
    except (ValueError, IndexError):
        return ""


def proper_entities(text: str) -> list[str]:
    raw = re.findall(r"\b(?:[A-Z][A-Za-z0-9'.-]+(?:\s+|$)){1,4}", text)
    cleaned=[]
    seen=set()
    blocked={"The","This","That","NBA","United States","American"}
    for value in raw:
        value=" ".join(value.split()).strip(" .,-")
        if len(value) < 3 or value in blocked:
            continue
        low=value.lower()
        if low not in seen:
            seen.add(low)
            cleaned.append(value)
    return cleaned


topic_id = arg_value("--topic-id")
topics = json.loads((ROOT / "production" / "topics.json").read_text(encoding="utf-8"))
row = next((x for x in topics.get("topics", []) if str(x.get("id")) == topic_id), None)
if row:
    topic = str(row.get("topic") or "NBA basketball").strip()
    research_path = ROOT / "production" / "research-cache" / topic_id / "research.json"
    research = json.loads(research_path.read_text(encoding="utf-8")) if research_path.exists() else {}
    corpus = " ".join([
        topic,
        str(row.get("working_angle") or ""),
        str(row.get("title_seed") or ""),
        str(research.get("thesis") or ""),
        " ".join(str(x.get("claim") or "") for x in research.get("facts", []) if isinstance(x, dict)),
        " ".join(str(x.get("event") or "") for x in research.get("timeline", []) if isinstance(x, dict)),
    ])
    entities = proper_entities(corpus)[:16]
    subject_words = [w for w in re.findall(r"[A-Za-z][A-Za-z'.-]+", topic) if len(w) >= 4]
    allow_terms = {e.lower() for e in entities}
    allow_terms.update(w.lower() for w in subject_words[:10])
    allow_terms.update({
        "basketball", "nba", "playoffs", "finals", "arena", "court", "game", "draft",
        "all-star", "all star", "coach", "player", "team", "jersey", "championship",
    })

    queries = [
        f"{topic} NBA basketball",
        f"{topic} basketball game",
        f"{topic} NBA arena",
        f"{topic} NBA playoffs",
        f"{topic} basketball player",
        f"{topic} basketball court",
    ]
    for entity in entities[:12]:
        queries.extend([
            f"{entity} NBA",
            f"{entity} basketball",
            f"{entity} basketball game",
        ])
    queries.extend([
        "NBA basketball arena game",
        "professional basketball court arena",
        "NBA draft basketball",
        "NBA playoffs basketball arena",
        "basketball crowd arena United States",
        "professional basketball player game United States",
    ])
    core.SUBJECT_PROFILES[topic.lower()] = {
        "queries": list(dict.fromkeys(queries))[:48],
        "allow_terms": allow_terms,
        "block_terms": {"ai generated", "concept render", "video game", "logo", "logos"},
    }

core.USER_AGENT = "NBAStars/1.0 (editorial visual research)"

if __name__ == "__main__":
    core.main()
