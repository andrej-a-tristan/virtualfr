"""DeliveryService — queues, stores, and retrieves milestone messages.

In-memory store with Supabase persistence (message_history table).
Supports: queue, list unread, mark read, dismiss.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from app.schemas.progression import MilestoneMessage, MilestoneMessageList

logger = logging.getLogger(__name__)

# ── In-memory message store ───────────────────────────────────────────────────
# Key: (user_id, girlfriend_id) → list of MilestoneMessage dicts
_pending_messages: dict[tuple[str, str], list[dict]] = defaultdict(list)


def queue_message(
    user_id: str,
    girlfriend_id: str,
    message: MilestoneMessage,
) -> str:
    """Queue a milestone message for delivery. Returns the message id."""
    msg_dict = message.model_dump()
    key = (user_id, girlfriend_id)
    _pending_messages[key].append(msg_dict)

    # Persist to Supabase
    _persist_to_db(user_id, girlfriend_id, msg_dict)

    logger.info(
        f"Queued {message.event_type} message for user={user_id[:8]} gf={girlfriend_id[:8]}"
    )
    return message.id


def get_messages(
    user_id: str,
    girlfriend_id: str,
    unread_only: bool = True,
    limit: int = 20,
) -> MilestoneMessageList:
    """Retrieve milestone messages. Optionally filter to unread only."""
    key = (user_id, girlfriend_id)

    # Try loading from DB if in-memory is empty
    if key not in _pending_messages or not _pending_messages[key]:
        _load_from_db(user_id, girlfriend_id)

    all_msgs = _pending_messages.get(key, [])

    if unread_only:
        filtered = [m for m in all_msgs if not m.get("read_at") and not m.get("dismissed")]
    else:
        filtered = all_msgs

    # Sort by sent_at descending (newest first)
    filtered.sort(key=lambda m: m.get("sent_at", ""), reverse=True)
    filtered = filtered[:limit]

    messages = [MilestoneMessage(**m) for m in filtered]
    unread_count = sum(1 for m in all_msgs if not m.get("read_at") and not m.get("dismissed"))

    return MilestoneMessageList(messages=messages, unread_count=unread_count)


def mark_read(user_id: str, girlfriend_id: str, message_ids: list[str]) -> int:
    """Mark messages as read. Returns count of messages updated."""
    key = (user_id, girlfriend_id)
    now = datetime.now(timezone.utc).isoformat()
    count = 0

    for msg in _pending_messages.get(key, []):
        if msg["id"] in message_ids and not msg.get("read_at"):
            msg["read_at"] = now
            count += 1

    # Persist to DB
    if count > 0:
        _update_read_in_db(user_id, message_ids, now)

    return count


def mark_clicked(user_id: str, girlfriend_id: str, message_id: str, action: str) -> bool:
    """Record a choice click on a milestone message."""
    key = (user_id, girlfriend_id)
    now = datetime.now(timezone.utc).isoformat()

    for msg in _pending_messages.get(key, []):
        if msg["id"] == message_id:
            msg["clicked_at"] = now
            msg["_clicked_action"] = action
            _update_click_in_db(user_id, message_id, now)
            return True
    return False


def dismiss_message(user_id: str, girlfriend_id: str, message_id: str) -> bool:
    """Dismiss a milestone message."""
    key = (user_id, girlfriend_id)

    for msg in _pending_messages.get(key, []):
        if msg["id"] == message_id:
            msg["dismissed"] = True
            _update_dismiss_in_db(user_id, message_id)
            return True
    return False


def get_unread_count(user_id: str, girlfriend_id: str) -> int:
    """Quick unread count for badge display."""
    key = (user_id, girlfriend_id)
    if key not in _pending_messages:
        _load_from_db(user_id, girlfriend_id)
    return sum(
        1 for m in _pending_messages.get(key, [])
        if not m.get("read_at") and not m.get("dismissed")
    )


# ── Supabase persistence ─────────────────────────────────────────────────────

def _persist_to_db(user_id: str, girlfriend_id: str, msg: dict) -> None:
    """Save a message to the message_history table."""
    try:
        from app.core.supabase_client import get_supabase_admin
        from uuid import UUID
        admin = get_supabase_admin()
        if not admin:
            return

        # Only persist for real UUID user_ids
        try:
            UUID(user_id)
            UUID(girlfriend_id)
        except (ValueError, TypeError):
            return

        admin.table("message_history").insert({
            "id": msg["id"],
            "user_id": user_id,
            "girlfriend_id": girlfriend_id,
            "event_type": msg["event_type"],
            "event_data": {"milestone_key": msg.get("milestone_key")},
            "content": msg.get("content", {}),
            "channel": "in_app",
            "experiment_variant": msg.get("experiment_variant"),
        }).execute()
    except Exception as exc:
        logger.warning(f"Failed to persist message to DB: {exc}")


def _load_from_db(user_id: str, girlfriend_id: str) -> None:
    """Load messages from DB into in-memory store."""
    try:
        from app.core.supabase_client import get_supabase_admin
        from uuid import UUID
        admin = get_supabase_admin()
        if not admin:
            return

        try:
            UUID(user_id)
            UUID(girlfriend_id)
        except (ValueError, TypeError):
            return

        res = (
            admin.table("message_history")
            .select("*")
            .eq("user_id", user_id)
            .eq("girlfriend_id", girlfriend_id)
            .order("sent_at", desc=True)
            .limit(50)
            .execute()
        )
        if res.data:
            key = (user_id, girlfriend_id)
            _pending_messages[key] = [
                {
                    "id": row["id"],
                    "event_type": row["event_type"],
                    "milestone_key": (row.get("event_data") or {}).get("milestone_key"),
                    "content": row.get("content", {}),
                    "sent_at": row.get("sent_at", ""),
                    "read_at": row.get("read_at"),
                    "dismissed": row.get("dismissed", False),
                    "experiment_variant": row.get("experiment_variant"),
                }
                for row in res.data
            ]
    except Exception as exc:
        logger.warning(f"Failed to load messages from DB: {exc}")


def _update_read_in_db(user_id: str, message_ids: list[str], read_at: str) -> None:
    try:
        from app.core.supabase_client import get_supabase_admin
        admin = get_supabase_admin()
        if admin:
            for mid in message_ids:
                admin.table("message_history").update({"read_at": read_at}).eq("id", mid).execute()
    except Exception:
        pass


def _update_click_in_db(user_id: str, message_id: str, clicked_at: str) -> None:
    try:
        from app.core.supabase_client import get_supabase_admin
        admin = get_supabase_admin()
        if admin:
            admin.table("message_history").update({"clicked_at": clicked_at}).eq("id", message_id).execute()
    except Exception:
        pass


def _update_dismiss_in_db(user_id: str, message_id: str) -> None:
    try:
        from app.core.supabase_client import get_supabase_admin
        admin = get_supabase_admin()
        if admin:
            admin.table("message_history").update({"dismissed": True}).eq("id", message_id).execute()
    except Exception:
        pass
