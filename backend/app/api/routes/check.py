"""Config check endpoint: API key and DB status (for ops). No secrets returned."""
from fastapi import APIRouter

router = APIRouter(prefix="/check", tags=["check"])


@router.get("")
def check_config():
    """Return API key and Supabase status. No secrets."""
    from app.core import get_api_key
    from app.core.supabase_client import get_supabase_admin, is_supabase_configured

    api_key = get_api_key()
    api_key_set = bool(api_key and len(api_key.strip()) > 0)

    supabase_configured = is_supabase_configured()
    supabase_ok = False
    db_tables = {}
    if supabase_configured:
        admin = get_supabase_admin()
        if admin:
            try:
                for table in ["users_profile", "girlfriends", "sessions"]:
                    r = admin.table(table).select("*").limit(1).execute()
                    db_tables[table] = "ok" if r.data is not None else "error"
                supabase_ok = True
            except Exception as e:
                db_tables["error"] = str(e)

    return {
        "api_key_set": api_key_set,
        "supabase_configured": supabase_configured,
        "supabase_ok": supabase_ok,
        "db_tables": db_tables,
    }
