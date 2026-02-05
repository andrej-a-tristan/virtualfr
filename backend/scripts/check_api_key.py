#!/usr/bin/env python3
"""Quick check: does backend/.env have a non-empty API_KEY? Run from backend: python scripts/check_api_key.py"""
from pathlib import Path

p = Path(__file__).resolve().parents[1] / ".env"
print("Reading:", p)
if not p.exists():
    print(".env not found at", p)
    exit(1)
text = p.read_text(encoding="utf-8-sig")
found = False
for i, line in enumerate(text.splitlines(), 1):
    s = line.strip()
    if s.startswith("API_KEY="):
        found = True
        raw_value = line.split("=", 1)[1]
        v = raw_value.strip()
        print("Line", i, "| value length:", len(v))
        if v:
            print("First 15 chars:", repr(v[:15]) + "...")
        else:
            print("PROBLEM: value is empty after API_KEY=")
            print("  Make sure the line is exactly: API_KEY=sk-proj-... (no space around =)")
            print("  Save backend/.env (Cmd+S) and run this script again.")
        if len(v) > 20:
            print("OK: key looks present")
        break
if not found:
    print("No line starting with API_KEY= found in .env")
