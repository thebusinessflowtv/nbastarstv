from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from production import generate_episode_v3_business_base as base


def nba_prompt(topic: dict[str, Any], research: dict[str, Any], editorial: dict[str, Any]) -> str:
    research_for_prompt = {
        "thesis": research.get("thesis"),
        "facts": research.get("facts"),
        "verified_numbers": research.get("verified_numbers"),
        "timeline": research.get("timeline"),
        "sources": research.get("sources"),
        "risk_flags": research.get("risk_flags"),
    }
    editorial_compact = {
        "packaging_strategy": editorial.get("packaging_strategy") or {},
        "rules": editorial.get("rules") or editorial.get("editorial_rules") or [],
    }
    return f"""
You are the documentary writer and YouTube packaging strategist for NBA Stars.
Write for a United States audience in natural American English. The channel covers NBA players, teams, rivalries, records, strange rules, rise-and-fall stories, forgotten careers, historic games and current stories reframed as compelling narratives.

TOPIC
{json.dumps(topic, ensure_ascii=False)}

CACHED RESEARCH BRIEF — THIS IS YOUR ONLY FACTUAL SOURCE
{json.dumps(research_for_prompt, ensure_ascii=False)}

EDITORIAL PACKAGING RULES
{json.dumps(editorial_compact, ensure_ascii=False)}

FACTUAL / SAFETY RULES
- DO NOT browse, search, fetch URLs, or use tools other than {base.core.EPISODE_TOOL_NAME}.
- Use only claims supported by the cached research brief. If a detail is absent, do not invent it.
- Never present a rumor as fact. Never invent quotes, statistics, injuries, trades, suspensions, relationships or motives.
- Clearly preserve important context such as season, era, playoff vs regular season, and whether a record is career/single-game when relevant.
- You may use aggressive curiosity and factual clickbait, but the actual title, hook and thumbnail concept must remain supportable.

STORYTELLING RULES
- Build a true story, not a generic list of facts.
- Open with immediate tension or a surprising contradiction in the first 15 seconds.
- Create an open loop in the first 30 seconds.
- Renew tension, reveal context or introduce a new question every 45-90 seconds.
- Use vivid but factual basketball language that a mainstream NBA fan understands.
- Avoid repetitive transitions and filler.
- End by resolving the central question instead of adding an unrelated outro.

MANDATORY OUTPUT
1. Write the full narration FIRST inside the tool input.
2. Narration must be 1,750-2,150 words.
3. Exactly 6 English title candidates, each <=100 characters, optimized for CTR while truthful.
4. Select one strongest title.
5. Exactly 3 thumbnail concepts, each with 0-4 words of optional thumbnail text and a clear visual concept.
6. Concise description, useful tags, one opening hook, and a concise chapter list.
7. Do not insert citations inside the spoken narration; source metadata is attached separately.

Call {base.core.EPISODE_TOOL_NAME} exactly once. Do not emit extra prose.
""".strip()


def _clip_title(value: Any, fallback: str) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip() or fallback
    if len(text) <= 100:
        return text
    clipped = text[:100].rstrip()
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0]
    return clipped[:100].rstrip(" -:,.|")


def _normalize_package_shape(data: dict[str, Any], topic: dict[str, Any]) -> None:
    topic_name = re.sub(r"\s+", " ", str(topic.get("topic") or "NBA Story")).strip()
    selected = _clip_title(data.get("selected_title"), topic_name)
    data["selected_title"] = selected

    raw_titles = [selected]
    raw_titles.extend(str(x) for x in (data.get("title_candidates") or []) if str(x).strip())
    fallback_titles = [
        topic_name,
        f"What Really Happened With {topic_name}",
        f"The Truth About {topic_name}",
        f"Why {topic_name} Matters Right Now",
        f"Inside {topic_name}",
        f"The NBA Story Behind {topic_name}",
    ]
    raw_titles.extend(fallback_titles)
    titles: list[str] = []
    seen: set[str] = set()
    for value in raw_titles:
        title = _clip_title(value, selected)
        key = title.casefold()
        if title and key not in seen:
            seen.add(key)
            titles.append(title)
        if len(titles) == 6:
            break
    data["title_candidates"] = titles[:6]

    thumbs: list[dict[str, str]] = []
    for item in data.get("thumbnail_variants") or []:
        if not isinstance(item, dict):
            continue
        text = " ".join(str(item.get("text") or "").split()[:4])
        concept = re.sub(r"\s+", " ", str(item.get("concept") or item.get("visual") or "")).strip()
        if not concept:
            concept = f"Cinematic NBA thumbnail centered on {topic_name}."
        thumbs.append({"text": text, "concept": concept})
        if len(thumbs) == 3:
            break
    thumb_defaults = [
        {"text": "STILL UNREAL", "concept": f"Extreme close-up NBA portrait tied to {topic_name}, dramatic arena lights and scoreboard context."},
        {"text": "HOW IS THIS POSSIBLE?", "concept": f"High-contrast action frame tied to {topic_name}, crowd depth, stat-board visual cue, no clutter."},
        {"text": "THE REAL STORY", "concept": f"Cinematic split-context NBA composition showing the central tension behind {topic_name}."},
    ]
    for item in thumb_defaults:
        if len(thumbs) >= 3:
            break
        thumbs.append(item)
    data["thumbnail_variants"] = thumbs[:3]

    if not str(data.get("hook") or "").strip():
        data["hook"] = f"The numbers tell one story about {topic_name}. The context tells another."


def validate_package(data: dict[str, Any], topic: dict[str, Any]) -> None:
    # Paid Sonnet outputs are cached before local validation. Normalize harmless
    # structural over-generation locally so a cached response with e.g. 10 title
    # candidates does not permanently block the production on every retry.
    _normalize_package_shape(data, topic)

    required = ["selected_title", "title_candidates", "thumbnail_variants", "description", "tags", "hook", "script", "chapters"]
    missing = [key for key in required if not data.get(key)]
    if missing:
        raise RuntimeError(f"Episode package missing: {', '.join(missing)}")
    title = str(data["selected_title"]).strip()
    if len(title) > 100:
        raise RuntimeError(f"YouTube title exceeds 100 chars: {len(title)}")
    titles = data.get("title_candidates") or []
    if len(titles) != 6:
        raise RuntimeError(f"Need exactly 6 title candidates, got {len(titles)}")
    if any(len(str(value)) > 100 for value in titles):
        raise RuntimeError("A title candidate exceeds 100 chars")
    thumbs = data.get("thumbnail_variants") or []
    if len(thumbs) != 3:
        raise RuntimeError(f"Need exactly 3 thumbnail variants, got {len(thumbs)}")
    for thumb in thumbs:
        if len(str(thumb.get("text") or "").split()) > 4:
            raise RuntimeError(f"Thumbnail text exceeds 4 words: {thumb.get('text')}")
    script_words = len(str(data["script"]).split())
    if not 1750 <= script_words <= 2150:
        raise RuntimeError(f"Script must be 1750-2150 words; got {script_words}")
    if len(str(data["description"])) > 5000:
        raise RuntimeError("YouTube description exceeds 5000 chars")
    storyboard = base.core.build_storyboard(str(data["script"]), topic)
    if len(storyboard) < 40:
        raise RuntimeError(f"Locally generated storyboard too short: {len(storyboard)} scenes")
    data["topic_id"] = topic["id"]
    data["topic"] = topic["topic"]
    data["script_word_count"] = script_words
    data["storyboard"] = storyboard


def write_outputs(package: dict[str, Any]) -> Path:
    output_dir = base.core.OUTPUT_ROOT / str(package["topic_id"])
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "episode-package.json").write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "script.txt").write_text(str(package["script"]).strip() + "\n", encoding="utf-8")
    (output_dir / "metadata.json").write_text(
        json.dumps({
            "title": package["selected_title"],
            "description": package["description"],
            "tags": package["tags"],
            "category_id": "17",
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "storyboard.json").write_text(json.dumps(package["storyboard"], ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "thumbnail.json").write_text(
        json.dumps({"selected_title": package["selected_title"], "variants": package["thumbnail_variants"]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_dir


base.build_prompt = nba_prompt
base.validate_package = validate_package
base.core.build_prompt = nba_prompt
base.core.validate_package = validate_package
base.core.write_outputs = write_outputs


if __name__ == "__main__":
    base.main()
