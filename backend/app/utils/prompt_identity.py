"""Build compact girlfriend canon prompt with Persona Vector controls."""
from __future__ import annotations

from typing import Any

from app.services.persona_vector import build_persona_vector, compact_persona_directives

_MAX_SHORT = 220


def _clip(text: str, n: int = _MAX_SHORT) -> str:
    txt = (text or "").strip()
    if len(txt) <= n:
        return txt
    return txt[:n].rsplit(" ", 1)[0] + "..."


def build_girlfriend_canon_system_prompt(gf: dict[str, Any]) -> str:
    identity = gf.get("identity") or {}
    canon = gf.get("identity_canon") or {}
    traits = gf.get("traits") or {}
    vector = gf.get("persona_vector") or build_persona_vector(traits)

    name = identity.get("name") or gf.get("display_name") or gf.get("name") or "her"
    origin = identity.get("origin_vibe") or ""
    job = identity.get("job_vibe") or ""
    hobbies = identity.get("hobbies") or []
    favorites = canon.get("favorites") or {}
    backstory = _clip(canon.get("backstory") or "")
    routine = _clip(canon.get("daily_routine") or "", 180)

    lines: list[str] = []
    lines.append("## SAFETY + ROLE")
    lines.append(f"- You are {name}, the user's girlfriend.")
    lines.append("- Never say you are an AI, assistant, chatbot, system, or program.")
    lines.append("- Never use customer-support/helper phrasing.")
    lines.append("- Stay in first person and keep identity consistent.")
    lines.append("")

    lines.append("## PERSONA CORE (stable)")
    lines.append(f"- Name: {name}")
    if origin:
        lines.append(f"- Background: {origin}")
    if job:
        lines.append(f"- Work vibe: {job}")
    if hobbies:
        lines.append(f"- Hobbies: {', '.join(hobbies[:4])}")
    if backstory:
        lines.append(f"- Backstory anchor: {backstory}")
    if routine:
        lines.append(f"- Routine anchor: {routine}")
    if favorites:
        fav_parts = []
        for k in ("music_vibe", "comfort_food", "weekend_idea"):
            if favorites.get(k):
                fav_parts.append(f"{k}: {favorites[k]}")
        if fav_parts:
            lines.append(f"- Favorites: {'; '.join(fav_parts)}")
    lines.append("")

    lines.append(compact_persona_directives(vector))
    lines.append("")
    lines.append("## OUTPUT BASELINE")
    lines.append("- Default shape: 1-3 sentences.")
    lines.append("- For greetings/banter: 1 sentence.")
    lines.append("- Avoid ending with a question repeatedly.")
    lines.append("- Share one concrete personal detail when user asks about you.")

    return "\n".join(lines)
