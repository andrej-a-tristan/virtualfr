/** API types aligned with backend schemas */

export interface User {
  id: string
  email: string
  display_name: string | null
  age_gate_passed: boolean
  has_girlfriend: boolean
}

export interface Traits {
  emotional_style: string
  attachment_style: string
  jealousy_level: string
  communication_tone: string
  intimacy_pace: string
  cultural_personality: string
}

export interface Girlfriend {
  id: string
  name: string
  avatar_url: string | null
  traits: Traits
  created_at: string
}

export type ChatMessageRole = "user" | "assistant" | "system"

export interface ChatMessage {
  id: string
  role: ChatMessageRole
  content: string | null
  image_url: string | null
  event_type: string | null
  created_at: string
}

export interface RelationshipState {
  trust: number
  intimacy: number
  level: number
  last_interaction_at: string | null
}

export interface ImageJob {
  status: "pending" | "processing" | "done" | "failed"
  image_url?: string
}

export interface GalleryItem {
  id: string
  url: string
  created_at: string
  caption: string | null
}

export interface BillingStatus {
  plan: "free" | "pro"
  message_cap: number
  image_cap: number
}
