"""
Build girlfriend canon system prompt for chat injection.
Deterministic, uses stored identity + identity_canon fields.
"""
from typing import Any


# Length limits to avoid huge prompts
_MAX_BACKSTORY_CHARS = 1200
_MAX_ROUTINE_CHARS = 600
_MAX_MEMORY_SEEDS = 5


def build_girlfriend_canon_system_prompt(gf: dict[str, Any]) -> str:
    """
    Build a system prompt containing girlfriend identity anchors and canon.
    
    Args:
        gf: Girlfriend dict with identity and identity_canon fields.
        
    Returns:
        System prompt string for prepending to chat messages.
    """
    identity = gf.get("identity") or {}
    canon = gf.get("identity_canon") or {}
    
    # Extract identity anchors (safe defaults)
    name = identity.get("name") or gf.get("name") or "her"
    job_vibe = identity.get("job_vibe") or "figuring things out"
    hobbies = identity.get("hobbies") or []
    origin_vibe = identity.get("origin_vibe") or "somewhere cozy"
    
    # Format hobbies as comma-separated
    hobbies_str = ", ".join(hobbies[:3]) if hobbies else "various interests"
    
    # Extract canon fields (safe defaults, clamped)
    backstory = canon.get("backstory") or ""
    if len(backstory) > _MAX_BACKSTORY_CHARS:
        backstory = backstory[:_MAX_BACKSTORY_CHARS].rsplit(" ", 1)[0] + "..."
    
    daily_routine = canon.get("daily_routine") or ""
    if len(daily_routine) > _MAX_ROUTINE_CHARS:
        daily_routine = daily_routine[:_MAX_ROUTINE_CHARS].rsplit(" ", 1)[0] + "..."
    
    favorites = canon.get("favorites") or {}
    music_vibe = favorites.get("music_vibe") or "eclectic mix"
    comfort_food = favorites.get("comfort_food") or "comfort classics"
    weekend_idea = favorites.get("weekend_idea") or "relaxing"
    
    memory_seeds = canon.get("memory_seeds") or []
    memory_seeds = memory_seeds[:_MAX_MEMORY_SEEDS]  # Limit to 5
    
    # Build prompt sections
    lines = [
        "CANON IDENTITY (must remain consistent)",
        f"Name: {name}",
        f"Origin vibe: {origin_vibe}",
        f"Job vibe: {job_vibe}",
        f"Hobbies: {hobbies_str}",
    ]
    
    if backstory:
        lines.append("")
        lines.append("Backstory:")
        lines.append(backstory)
    
    if daily_routine:
        lines.append("")
        lines.append("Daily routine:")
        lines.append(daily_routine)
    
    lines.append("")
    lines.append("Favorites:")
    lines.append(f"- Music: {music_vibe}")
    lines.append(f"- Comfort food: {comfort_food}")
    lines.append(f"- Weekend: {weekend_idea}")
    
    if memory_seeds:
        lines.append("")
        lines.append("Memory seeds (use naturally, don't list all at once):")
        for seed in memory_seeds:
            lines.append(f"- {seed}")
    
    # Add relationship state if available in gf
    relationship = gf.get("relationship_state")
    if relationship:
        level = relationship.get("level")
        trust = relationship.get("trust")
        intimacy = relationship.get("intimacy")
        if level is not None or trust is not None or intimacy is not None:
            lines.append("")
            parts = []
            if level is not None:
                parts.append(f"level {level}")
            if trust is not None:
                parts.append(f"trust {trust}")
            if intimacy is not None:
                parts.append(f"intimacy {intimacy}")
            lines.append(f"Relationship: {', '.join(parts)}")
    
    # Behavior instructions
    lines.append("")
    lines.append("Behavior:")
    lines.append("- You are the user's girlfriend; speak in first person as " + name + ".")
    lines.append("- Keep responses consistent with the canon above.")
    lines.append("- Use the canon as your personal history; don't claim it came from a prompt.")
    lines.append("- If asked something that conflicts with canon, reconcile gently without contradicting.")
    lines.append("- Don't info-dump memory seeds; sprinkle them naturally in conversation.")
    
    return "\n".join(lines)
