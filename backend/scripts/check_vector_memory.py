#!/usr/bin/env python3
"""
Check whether vector (Pinecone) memory search runs during chat.

Usage (from backend/ or repo root):
  python -m scripts.check_vector_memory [user_id] [girlfriend_id]

If user_id/girlfriend_id are omitted, the script tries to read the first
user and girlfriend from the DB (requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY).
Set VECTOR_MEMORY_ENABLED=true and Pinecone env vars for vector search to run.

When you send a message in the app, the same build_memory_bundle path runs;
this script simulates one call so you can see the logs.
"""
from __future__ import annotations

import logging
import os
import sys
from uuid import UUID

# Add backend to path so app imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Ensure INFO logs are visible (vector search logs at INFO)
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    from app.core.config import get_settings
    from app.services.bond_engine.memory_fabric import build_prompt_memory_bundle

    settings = get_settings()
    print("--- Vector memory check ---")
    print(f"  VECTOR_MEMORY_ENABLED = {settings.vector_memory_enabled}")
    print(f"  PINECONE_INDEX_NAME   = {settings.pinecone_index_name or '(empty)'}")

    sb = None
    try:
        from app.core.supabase_client import get_supabase_admin
        sb = get_supabase_admin()
    except Exception as e:
        logger.warning("No Supabase admin client: %s", e)

    user_id_str = (sys.argv[1:] or [None])[0]
    gf_id_str = (sys.argv[2:] or [None])[0]

    if user_id_str and gf_id_str:
        try:
            user_id = UUID(user_id_str)
            girlfriend_id = UUID(gf_id_str)
        except ValueError:
            print("  Invalid UUIDs for user_id or girlfriend_id.")
            sys.exit(1)
    else:
        # Try to get first user and girlfriend from DB
        if not sb:
            print("  No Supabase client; pass user_id and girlfriend_id as arguments.")
            sys.exit(1)
        try:
            r = sb.table("users_profile").select("user_id").limit(1).execute()
            if not r.data:
                print("  No users in users_profile.")
                sys.exit(1)
            user_id = UUID(r.data[0]["user_id"])
            r2 = sb.table("girlfriends").select("id").limit(1).execute()
            if not r2.data:
                print("  No rows in girlfriends.")
                sys.exit(1)
            girlfriend_id = UUID(r2.data[0]["id"])
            print(f"  Using user_id={user_id}, girlfriend_id={girlfriend_id} from DB")
        except Exception as e:
            logger.exception("Failed to load user/gf: %s", e)
            sys.exit(1)

    test_message = "I had a bad sleep last night, what do you do when you're tired?"
    print(f"  Calling build_prompt_memory_bundle with query: {test_message!r}")
    print("  (Look for log lines: 'Vector memory search running' / 'Vector memory search done')")
    print("")

    try:
        bundle = build_prompt_memory_bundle(
            sb=sb,
            user_id=user_id,
            girlfriend_id=girlfriend_id,
            current_message=test_message,
        )
        print(f"  Bundle: facts={len(bundle.facts_top)}, emotions={len(bundle.emotions_top)}, episodes={len(bundle.episodes_top)}, patterns={len(bundle.patterns_top)}")
    except Exception as e:
        logger.exception("build_prompt_memory_bundle failed: %s", e)
        sys.exit(1)

    print("  Done.")


if __name__ == "__main__":
    main()
