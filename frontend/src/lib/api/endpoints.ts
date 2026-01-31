/** API endpoint helpers and response types */
import {
  apiGet,
  apiPost,
} from "./client"
import type {
  User,
  Girlfriend,
  Traits,
  ChatMessage,
  RelationshipState,
  GalleryItem,
  BillingStatus,
  ImageJob,
} from "./types"

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
export async function createGirlfriend(traits: Traits) {
  return apiPost<Girlfriend>("/girlfriends", traits)
}
export async function getCurrentGirlfriend() {
  return apiGet<Girlfriend>("/girlfriends/current")
}

// Chat
export async function getChatHistory() {
  return apiGet<{ messages: ChatMessage[] }>("/chat/history")
}
export async function getChatState() {
  return apiGet<RelationshipState>("/chat/state")
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
