/** API endpoint helpers and response types */
import { apiGet, apiPost } from "./client"
import type {
  User,
  Girlfriend,
  TraitSelection,
  ChatMessage,
  RelationshipState,
  GalleryItem,
  BillingStatus,
  ImageJob,
  MemoryContext,
  MemorySummary,
  MemoryItemsResponse,
  MemoryType,
  FactualMemoryItem,
  EmotionalMemoryItem,
} from "./types"

/** Convert TraitSelection (camelCase) to API snake_case. */
function traitsToApi(t: TraitSelection) {
  return {
    emotional_style: t.emotionalStyle,
    attachment_style: t.attachmentStyle,
    reaction_to_absence: t.reactionToAbsence,
    communication_style: t.communicationStyle,
    relationship_pace: t.relationshipPace,
    cultural_personality: t.culturalPersonality,
  }
}

/** Convert API traits (snake_case) to TraitSelection (camelCase). */
function traitsFromApi(t: Record<string, string>): TraitSelection {
  return {
    emotionalStyle: t.emotional_style as TraitSelection["emotionalStyle"],
    attachmentStyle: t.attachment_style as TraitSelection["attachmentStyle"],
    reactionToAbsence: t.reaction_to_absence as TraitSelection["reactionToAbsence"],
    communicationStyle: t.communication_style as TraitSelection["communicationStyle"],
    relationshipPace: t.relationship_pace as TraitSelection["relationshipPace"],
    culturalPersonality: t.cultural_personality as TraitSelection["culturalPersonality"],
  }
}

// Auth
export async function signup(email: string, password: string, displayName?: string) {
  return apiPost<{ ok: boolean; user: User }>("/auth/signup", { email, password, display_name: displayName })
}
export async function login(email: string, password: string) {
  return apiPost<{ ok: boolean; user: User }>("/auth/login", { email, password })
}
export async function logout() {
  return apiPost<{ ok: boolean }>("/auth/logout")
}

// Me
export async function getMe() {
  return apiGet<User>("/me")
}
export async function postAgeGate() {
  return apiPost<{ ok: boolean }>("/me/age-gate")
}

// Girlfriends
export interface CreateGirlfriendPayload {
  displayName: string
  traits: TraitSelection
}

export async function createGirlfriend(payload: CreateGirlfriendPayload): Promise<Girlfriend> {
  const raw = await apiPost<{
    id: string
    display_name: string
    traits: Record<string, string>
    created_at: string
  }>("/girlfriends", {
    display_name: payload.displayName,
    traits: traitsToApi(payload.traits),
  })
  return {
    id: raw.id,
    display_name: raw.display_name,
    traits: traitsFromApi(raw.traits),
    created_at: raw.created_at,
  }
}

export async function getCurrentGirlfriend(): Promise<Girlfriend | null> {
  try {
    const raw = await apiGet<{
      id: string
      display_name: string
      traits: Record<string, string>
      created_at: string
    }>("/girlfriends/current")
    return {
      id: raw.id,
      display_name: raw.display_name,
      traits: traitsFromApi(raw.traits),
      created_at: raw.created_at,
    }
  } catch {
    return null
  }
}

// Chat
export async function getChatHistory() {
  return apiGet<{ messages: ChatMessage[] }>("/chat/history")
}
export async function getChatState() {
  return apiGet<RelationshipState>("/chat/state")
}
export interface ChatAppOpenPayload {
  messages: ChatMessage[]
  relationshipState: RelationshipState
}
export async function postChatAppOpen(girlfriendId: string): Promise<ChatAppOpenPayload> {
  return apiPost<ChatAppOpenPayload>("/chat/app_open", { girlfriend_id: girlfriendId })
}
export function getChatSendStreamUrl() {
  return "/api/chat/send"
}

// Images
export async function requestImage() {
  return apiPost<{ job_id: string }>("/images/request")
}
export async function getImageJob(jobId: string) {
  return apiGet<ImageJob>(`/images/jobs/${jobId}`)
}
export async function getGallery() {
  return apiGet<{ items: GalleryItem[] }>("/images/gallery")
}

// Billing
export async function getBillingStatus() {
  return apiGet<BillingStatus>("/billing/status")
}
export async function checkout() {
  return apiPost<{ checkout_url: string }>("/billing/checkout")
}

// Moderation
export async function report() {
  return apiPost<{ ok: boolean }>("/moderation/report")
}

// -----------------------------------------------------------------------------
// Memory System (Task 1.2)
// -----------------------------------------------------------------------------

/** Get compact memory context for prompt building. */
export async function getMemorySummaryContext(girlfriendId?: string): Promise<MemoryContext> {
  const params = girlfriendId ? `?girlfriendId=${girlfriendId}` : ""
  return apiGet<MemoryContext>(`/memory/summary${params}`)
}

/** Get raw factual memory items. */
export async function getFactualMemoryItems(girlfriendId?: string, limit = 50): Promise<MemoryItemsResponse<FactualMemoryItem>> {
  const params = new URLSearchParams({ type: "factual", limit: String(limit) })
  if (girlfriendId) params.set("girlfriendId", girlfriendId)
  return apiGet<MemoryItemsResponse<FactualMemoryItem>>(`/memory/items?${params}`)
}

/** Get raw emotional memory items. */
export async function getEmotionalMemoryItems(girlfriendId?: string, limit = 50): Promise<MemoryItemsResponse<EmotionalMemoryItem>> {
  const params = new URLSearchParams({ type: "emotional", limit: String(limit) })
  if (girlfriendId) params.set("girlfriendId", girlfriendId)
  return apiGet<MemoryItemsResponse<EmotionalMemoryItem>>(`/memory/items?${params}`)
}

/** Get memory statistics and recent items. */
export async function getMemoryStats(girlfriendId?: string): Promise<MemorySummary> {
  const params = girlfriendId ? `?girlfriendId=${girlfriendId}` : ""
  return apiGet<MemorySummary>(`/memory/stats${params}`)
}
