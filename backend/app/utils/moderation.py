"""Text moderation utility using OpenAI moderation API or fallback denylist."""
import os
import logging
from typing import Tuple

import httpx

logger = logging.getLogger(__name__)

# Minimal denylist for fallback when no API key is configured
# Keep this small and obvious - only the worst terms
_DENYLIST = {
    # Slurs and highly offensive terms (redacted for brevity, add as needed)
    "slut", "whore", "bitch", "cunt", "nigger", "nigga", "faggot", "fag",
    "retard", "tranny", "chink", "spic", "kike",
    # Sexual terms inappropriate for names
    "pussy", "cock", "dick", "penis", "vagina", "anal", "sex", "porn",
    "cumslut", "fucktoy", "sexdoll",
}


def _check_denylist(text: str) -> bool:
    """Check if text contains any denylist terms. Returns True if clean."""
    lower = text.lower()
    for term in _DENYLIST:
        if term in lower:
            return False
    return True


async def moderate_text(text: str) -> Tuple[bool, str | None]:
    """
    Check if text is appropriate using OpenAI moderation or fallback.
    
    Returns:
        (allowed: bool, reason: str | None)
        - allowed=True means the text is OK
        - allowed=False means it was flagged, reason contains category
    """
    api_key = os.environ.get("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")
    
    if not api_key:
        # Fallback to denylist
        logger.warning("No OPENAI_API_KEY configured, using denylist fallback for moderation")
        if _check_denylist(text):
            return True, None
        return False, "denylist"
    
    # Use OpenAI moderation API
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/moderations",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "omni-moderation-latest",
                    "input": text,
                },
            )
            response.raise_for_status()
            data = response.json()
            
            results = data.get("results", [])
            if not results:
                return True, None
            
            result = results[0]
            if result.get("flagged", False):
                # Find which category was flagged
                categories = result.get("categories", {})
                flagged_cats = [cat for cat, flagged in categories.items() if flagged]
                reason = ", ".join(flagged_cats) if flagged_cats else "flagged"
                logger.info(f"Moderation flagged text: {reason}")
                return False, reason
            
            return True, None
            
    except httpx.HTTPStatusError as e:
        logger.error(f"OpenAI moderation API error: {e.response.status_code}")
        # Fall back to denylist on API error
        if _check_denylist(text):
            return True, None
        return False, "denylist"
    except Exception as e:
        logger.error(f"Moderation error: {e}")
        # Fall back to denylist on any error
        if _check_denylist(text):
            return True, None
        return False, "denylist"


def moderate_text_sync(text: str) -> Tuple[bool, str | None]:
    """
    Synchronous version using denylist only.
    Use moderate_text for async endpoints with API support.
    """
    if _check_denylist(text):
        return True, None
    return False, "denylist"
