# Backend: Connect FastAPI to Supabase and API Key

This guide configures the FastAPI backend to use **Supabase** (database/auth) and an **API key** (e.g. for external AI services). All secrets go in `.env`; never commit real keys.

---

## 1. Create `.env` in the backend folder

From the repo root:

```bash
cd backend
cp .env.example .env
```

Edit `backend/.env` and set the variables below.

---

## 2. Supabase

Use your **Project URL** and **anon (public) key** from the Supabase dashboard:

- Open [Supabase Dashboard](https://supabase.com/dashboard) → your project.
- Go to **Settings** → **API**.
- Copy **Project URL** and **anon public** key.

In `backend/.env`:

```env
# Example: if your project is at https://qzbiudxpeepbepclnkoq.supabase.co
SUPABASE_URL=https://qzbiudxpeepbepclnkoq.supabase.co
SUPABASE_ANON_KEY=<paste your anon key from Supabase Dashboard → Settings → API>
```

- Use the **anon** key for normal backend use (Row Level Security applies).
- For admin-only operations you can add `SUPABASE_SERVICE_ROLE_KEY` later (keep it secret).

**Publishable key:** If you have a “publishable” key (e.g. `sb_publishable_...`), that is for client-side usage. For this FastAPI backend use the **anon** key from the API settings.

---

## 3. API key (e.g. OpenAI)

For the FastAPI framework to call external APIs (e.g. OpenAI), set:

```env
API_KEY=<paste your API key here>
```

Example: if the key is for OpenAI, the app will read `API_KEY` and use it in HTTP headers or client config when calling that service. **Do not commit this value**; keep it only in `.env` (and ensure `.env` is in `.gitignore`).

---

## 4. Verify

- Ensure `backend/.env` is listed in `backend/.gitignore` or the root `.gitignore` so it is never committed.
- Start the backend:

```bash
cd backend
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

- The app uses `get_supabase()` from `app.core.supabase_client`: if `SUPABASE_URL` and `SUPABASE_ANON_KEY` are set, it returns a Supabase client; otherwise it returns `None` and the app can keep using in-memory storage.

---

## 5. Security checklist

- [ ] `.env` exists only in `backend/` and is **not** committed.
- [ ] `SUPABASE_ANON_KEY` is the anon key from Supabase **Settings → API**.
- [ ] `API_KEY` is stored only in `.env` and used in server-side code (never in frontend).
- [ ] For production, use a real secret manager or env vars provided by your host; do not paste keys into docs or code.

---

## Quick reference

| Variable             | Where to get it                    | Used for              |
|----------------------|------------------------------------|------------------------|
| `SUPABASE_URL`       | Supabase → Settings → API          | Supabase client        |
| `SUPABASE_ANON_KEY`  | Supabase → Settings → API (anon)   | Supabase client        |
| `API_KEY`            | Your API provider (e.g. OpenAI)    | External API calls     |

After editing `.env`, restart the FastAPI server so it picks up the new values.
