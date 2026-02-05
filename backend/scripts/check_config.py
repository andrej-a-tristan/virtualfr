#!/usr/bin/env python3
"""Check API key and DB status via the running backend. Usage: python scripts/check_config.py [base_url]
Requires backend running (e.g. uvicorn app.main:app --reload --port 8000)."""
import json
import sys
import urllib.request

BASE_URL = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")


def main():
    errors = []
    ok = []

    try:
        req = urllib.request.Request(f"{BASE_URL}/api/check")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print("[FAIL] Backend not reachable:", e)
        print("       Start: cd backend && uvicorn app.main:app --reload --port 8000")
        sys.exit(1)

    if data.get("api_key_set"):
        ok.append("API_KEY is set (backend loaded it from backend/.env)")
    else:
        errors.append("API_KEY not set. Add API_KEY=sk-... to backend/.env and restart backend.")

    if data.get("supabase_configured"):
        ok.append("Supabase configured")
        if data.get("supabase_ok"):
            for table, status in data.get("db_tables", {}).items():
                if table != "error":
                    ok.append(f"  {table}: {status}")
            if "error" in data.get("db_tables", {}):
                errors.append("DB error: " + data["db_tables"]["error"])
        else:
            errors.append("Supabase DB not OK (check SUPABASE_SERVICE_ROLE_KEY and run supabase_schema.sql)")
    else:
        errors.append("Supabase not configured (SUPABASE_* in backend/.env)")

    for s in ok:
        print("[OK]", s)
    for s in errors:
        print("[FAIL]", s)

    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
