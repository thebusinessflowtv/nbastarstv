from __future__ import annotations

import re
from typing import Any

try:
    from production import generate_episode_v3 as v3
    from production import recover_paid_episode as recovery
except ModuleNotFoundError:
    import generate_episode_v3 as v3
    import recover_paid_episode as recovery

# The NBA workflow deliberately caches the paid Sonnet response before validation.
# That means a structurally imperfect response can be reused on every retry unless
# recovery normalizes the fields that the NBA validator enforces. Keep the paid
# response, repair it locally, and only then run the final validator.
_original_repair_package = recovery.repair_package


def _clean_title(value: Any, fallback: str) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip() or fallback
    if len(text) <= 100:
        return text
    clipped = text[:100].rstrip()
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0]
    return clipped[:100].rstrip(" -:,.|")


def _title_candidates(package: dict[str, Any], topic: dict[str, Any]) -> list[str]:
    topic_name = re.sub(r"\s+", " ", str(topic.get("topic") or "NBA Story")).strip()
    selected = _clean_title(package.get("selected_title"), topic_name)
    existing = package.get("title_candidates") or []
    raw: list[str] = [selected]
    raw.extend(str(x) for x in existing if str(x).strip())
    raw.extend([
        topic_name,
        f"What Really Happened With {topic_name}",
        f"The Truth About {topic_name}",
        f"Why {topic_name} Matters Right Now",
        f"Inside {topic_name}",
        f"The NBA Story Behind {topic_name}",
    ])
    out: list[str] = []
    seen: set[str] = set()
    for value in raw:
        title = _clean_title(value, selected)
        key = title.casefold()
        if title and key not in seen:
            seen.add(key)
            out.append(title)
        if len(out) == 6:
            break
    while len(out) < 6:
        suffix = len(out) + 1
        candidate = _clean_title(f"{selected} — Part {suffix}", selected)
        if candidate.casefold() not in seen:
            seen.add(candidate.casefold())
            out.append(candidate)
        else:
            out.append(_clean_title(f"NBA Story {suffix}: {topic_name}", selected))
    return out[:6]


def _thumbnail_variants(package: dict[str, Any], topic: dict[str, Any]) -> list[dict[str, str]]:
    topic_name = re.sub(r"\s+", " ", str(topic.get("topic") or "NBA story")).strip()
    existing = package.get("thumbnail_variants") or []
    out: list[dict[str, str]] = []
    for item in existing:
        if not isinstance(item, dict):
            continue
        text = " ".join(str(item.get("text") or "").split()[:4])
        concept = re.sub(r"\s+", " ", str(item.get("concept") or item.get("visual") or "")).strip()
        if not concept:
            concept = f"Cinematic NBA thumbnail centered on {topic_name}."
        out.append({"text": text, "concept": concept})
        if len(out) == 3:
            break
    defaults = [
        {"text": "STILL UNREAL", "concept": f"Extreme close-up NBA portrait tied to {topic_name}, dramatic arena lights and scoreboard context."},
        {"text": "HOW IS THIS POSSIBLE?", "concept": f"High-contrast action frame tied to {topic_name}, crowd depth, stat-board visual cue, no clutter."},
        {"text": "THE REAL STORY", "concept": f"Cinematic split-context NBA composition showing the central tension behind {topic_name}."},
    ]
    for item in defaults:
        if len(out) >= 3:
            break
        out.append(item)
    return out[:3]


def _trim_long_script(script: str, max_words: int = 2100) -> str:
    words = script.split()
    if len(words) <= 2150:
        return script
    target = " ".join(words[:max_words]).strip()
    # Prefer ending at a complete sentence if one exists near the cutoff.
    last = max(target.rfind(". "), target.rfind("! "), target.rfind("? "))
    if last >= int(len(target) * 0.8):
        target = target[: last + 1]
    if target and target[-1] not in ".!?”\"'":
        target += "."
    return target


def repair_package_nba(package: dict[str, Any], topic: dict[str, Any], research: dict[str, Any]) -> dict[str, Any]:
    repaired = _original_repair_package(package, topic, research)
    topic_name = re.sub(r"\s+", " ", str(topic.get("topic") or "NBA Story")).strip()

    repaired["selected_title"] = _clean_title(repaired.get("selected_title"), topic_name)
    repaired["title_candidates"] = _title_candidates(repaired, topic)
    repaired["thumbnail_variants"] = _thumbnail_variants(repaired, topic)

    if not str(repaired.get("hook") or "").strip():
        repaired["hook"] = f"The numbers tell one story about {topic_name}. The context tells another."

    script = re.sub(r"\s+", " ", str(repaired.get("script") or "")).strip()
    repaired["script"] = _trim_long_script(script)

    # If the legacy recovery expanded a short script, keep it. If it is still
    # short after normalization, run the same source-backed local expansion once
    # more so no additional Anthropic request is needed.
    if len(repaired["script"].split()) < 1750:
        expanded, ok = recovery.expand_short_script_from_research(
            repaired["script"], topic, research, target_words=1850
        )
        if ok:
            repaired["script"] = expanded

    if not repaired.get("chapters"):
        repaired["chapters"] = recovery.deterministic_chapters(repaired["script"], topic)

    return repaired


recovery.repair_package = repair_package_nba
recovery.finalize_package = v3.core.finalize_package


if __name__ == "__main__":
    recovery.main()
