/** API client with credentials for cookie-based auth */
const BASE = "/api"

function getErrorMessage(res: Response, fallback: string): string {
  if (res.status === 404) {
    return "Backend not reachable. Is it running on port 8000? Start it with: cd backend && uvicorn app.main:app --reload --port 8000"
  }
  if (res.status === 502 || res.status === 503) {
    return "Cannot reach backend. Start it with: cd backend && uvicorn app.main:app --reload --port 8000"
  }
  return fallback
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${BASE}${path}`, {
      ...init,
      credentials: "include",
      headers: { "Content-Type": "application/json", ...init?.headers },
    })
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Network error"
    throw new Error(
      msg.includes("Failed") || msg.includes("fetch")
        ? "Cannot reach backend. Start it with: cd backend && uvicorn app.main:app --reload --port 8000"
        : msg
    )
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    const fallback = (err as { error?: string }).error || res.statusText
    throw new Error(getErrorMessage(res, fallback))
  }
  if (res.headers.get("content-type")?.includes("application/json")) return res.json() as Promise<T>
  return undefined as T
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return apiFetch<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined })
}

export async function apiGet<T>(path: string): Promise<T> {
  return apiFetch<T>(path, { method: "GET" })
}
