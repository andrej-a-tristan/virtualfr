"""Leaks collection — per-girlfriend leaked photos unlocked via paid slot spins."""
import hashlib
import logging
import random
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.api.store import (
    get_session_user,
    _persist,
)
from app.services.stripe_payments import create_one_time_payment

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/leaks", tags=["leaks"])

# ── In-memory storage ─────────────────────────────────────────────────────────
# Shared reference with store.py's _leaks_unlocked
from app.api.store import _leaks_unlocked

# ── Leak catalog ──────────────────────────────────────────────────────────────

LEAK_IDS_BY_RARITY: dict[str, list[str]] = {
    "COMMON": [
        "lk_mirror_selfie", "lk_gym_snap", "lk_morning_bed", "lk_pouty_lips",
        "lk_sundress", "lk_car_selfie", "lk_beach_walk", "lk_night_out",
        "lk_oversized_tee", "lk_pool_side", "lk_back_glance", "lk_yoga_pose",
        "lk_wet_hair", "lk_couch_lounge", "lk_sunset_silhouette", "lk_coffee_morning",
        "lk_fitting_room", "lk_tongue_out",
    ],
    "UNCOMMON": [
        "lk_lace_lingerie", "lk_bodysuit", "lk_stockings", "lk_braless",
        "lk_bubble_bath", "lk_red_lingerie", "lk_silk_robe", "lk_thong_peek",
        "lk_bikini_string", "lk_crop_underboob", "lk_mirror_lingerie", "lk_corset",
    ],
    "RARE": [
        "lk_topless_back", "lk_hand_bra", "lk_see_through", "lk_shower_glass",
        "lk_body_oil", "lk_bed_sheets", "lk_whipped_cream", "lk_skinny_dip",
        "lk_painting_nude", "lk_wet_tshirt",
    ],
    "EPIC": [
        "lk_full_nude_mirror", "lk_bath_nude", "lk_bed_spread",
        "lk_balcony_nude", "lk_oil_massage", "lk_selfie_nude",
    ],
    "LEGENDARY": [
        "lk_private_video", "lk_all_fours", "lk_spread_legs", "lk_ultimate",
    ],
}

ALL_LEAK_IDS: list[str] = []
for ids in LEAK_IDS_BY_RARITY.values():
    ALL_LEAK_IDS.extend(ids)

RARITY_WEIGHTS = {
    "COMMON": 0.50,
    "UNCOMMON": 0.25,
    "RARE": 0.15,
    "EPIC": 0.07,
    "LEGENDARY": 0.03,
}

# ── Slot box definitions ──────────────────────────────────────────────────────

LEAK_BOXES: dict[str, dict] = {
    "peek": {
        "id": "peek",
        "name": "Quick Peek",
        "price_eur": 1.99,
        "weights": {"COMMON": 0.65, "UNCOMMON": 0.25, "RARE": 0.08, "EPIC": 0.02, "LEGENDARY": 0.0},
    },
    "private": {
        "id": "private",
        "name": "Private Collection",
        "price_eur": 4.99,
        "weights": {"COMMON": 0.25, "UNCOMMON": 0.35, "RARE": 0.25, "EPIC": 0.12, "LEGENDARY": 0.03},
    },
    "uncensored": {
        "id": "uncensored",
        "name": "Fully Uncensored",
        "price_eur": 9.99,
        "weights": {"COMMON": 0.0, "UNCOMMON": 0.10, "RARE": 0.30, "EPIC": 0.40, "LEGENDARY": 0.20},
    },
}

SESSION_COOKIE = "session"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _session_id(request: Request) -> str | None:
    return (
        request.cookies.get("session")
        or request.cookies.get("session_id")
        or request.headers.get("x-session-id")
        or None
    )


def _resolve_gf(session_id: str, girlfriend_id: str | None) -> str:
    if girlfriend_id:
        return girlfriend_id
    user = get_session_user(session_id)
    return (user or {}).get("current_girlfriend_id", "")


def _require_user(request: Request) -> tuple[str, dict]:
    sid = _session_id(request)
    if not sid:
        raise HTTPException(status_code=401, detail="unauthorized")
    user = get_session_user(sid)
    if not user:
        raise HTTPException(status_code=401, detail="unauthorized")
    return sid, user


def get_unlocked_leaks(session_id: str, girlfriend_id: str | None = None) -> dict[str, str]:
    gf = _resolve_gf(session_id, girlfriend_id)
    if not gf:
        return {}
    return dict(_leaks_unlocked.get((session_id, gf), {}))


def _pick_random_leak(weights: dict[str, float], already: dict[str, str]) -> tuple[str, str] | None:
    """Pick a random leak weighted by rarity. Returns (rarity, leak_id) or None."""
    locked_by_rarity: dict[str, list[str]] = {}
    for rarity, ids in LEAK_IDS_BY_RARITY.items():
        locked = [lid for lid in ids if lid not in already]
        if locked and weights.get(rarity, 0) > 0:
            locked_by_rarity[rarity] = locked

    if not locked_by_rarity:
        return None

    candidates: list[tuple[str, str]] = []
    w_list: list[float] = []
    for rarity, ids in locked_by_rarity.items():
        w = weights.get(rarity, 0)
        per_item = w / len(ids)
        for lid in ids:
            candidates.append((rarity, lid))
            w_list.append(per_item)

    return random.choices(candidates, weights=w_list, k=1)[0]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/collection")
def get_leaks_collection(request: Request, girlfriend_id: str | None = None):
    """Return all unlocked leaks for the current girlfriend."""
    sid = _session_id(request)
    if not sid:
        return {"unlocked": {}, "total": len(ALL_LEAK_IDS)}

    user = get_session_user(sid)
    if not user:
        return {"unlocked": {}, "total": len(ALL_LEAK_IDS)}

    gf = girlfriend_id or user.get("current_girlfriend_id", "")
    unlocked = get_unlocked_leaks(sid, gf)

    return {
        "unlocked": unlocked,
        "total": len(ALL_LEAK_IDS),
    }


class LeakSpinRequest(BaseModel):
    box_id: str
    girlfriend_id: str | None = None


@router.post("/spin")
def spin_leak_slot(request: Request, body: LeakSpinRequest):
    """Charge the user's saved card, pick a random leak, and return it."""
    sid, user = _require_user(request)

    box = LEAK_BOXES.get(body.box_id)
    if not box:
        raise HTTPException(status_code=400, detail="Invalid box_id")

    gf = body.girlfriend_id or user.get("current_girlfriend_id", "")
    if not gf:
        raise HTTPException(status_code=400, detail="no_girlfriend")

    already = _leaks_unlocked.get((sid, gf), {})

    chosen = _pick_random_leak(box["weights"], already)
    if not chosen:
        return {"status": "sold_out", "error": "All leaks in this tier are already unlocked!"}

    chosen_rarity, chosen_id = chosen

    # ── Charge via unified helper ───────────────────────────────────────────
    amount_cents = int(round(box["price_eur"] * 100))
    result = create_one_time_payment(
        sid=sid,
        user=user,
        amount_cents=amount_cents,
        currency="eur",
        description=f"Leak Slot: {box['name']}",
        metadata={
            "type": "leak_slot",
            "box_id": body.box_id,
            "leak_id": chosen_id,
            "session_id": sid,
            "girlfriend_id": gf,
        },
        idempotency_extra=f"legacy_leaks_spin:{body.box_id}:{chosen_id}:{gf}",
    )

    if result.status == "no_card":
        return {"status": "no_card", "error": "No card on file. Please add a card first."}
    if result.status == "requires_action":
        return {
            "status": "requires_action",
            "client_secret": result.client_secret,
            "payment_intent_id": result.payment_intent_id,
            "leak_id": chosen_id,
            "rarity": chosen_rarity,
        }
    if result.status != "succeeded":
        return {"status": "failed", "error": result.error or "Payment failed. Please try again."}

    # ── Unlock the leak ───────────────────────────────────────────────────
    seed = hashlib.md5(f"{gf}:{chosen_id}".encode()).hexdigest()[:10]
    image_url = f"https://picsum.photos/seed/{seed}/400/600"

    key = (sid, gf)
    if key not in _leaks_unlocked:
        _leaks_unlocked[key] = {}
    _leaks_unlocked[key][chosen_id] = image_url
    _persist()

    logger.info("Leak slot: %s unlocked %s (rarity=%s, box=%s)",
                sid[:8], chosen_id, chosen_rarity, body.box_id)

    return {
        "status": "succeeded",
        "leak_id": chosen_id,
        "rarity": chosen_rarity,
        "image_url": image_url,
    }
