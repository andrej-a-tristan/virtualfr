/** API types aligned with backend schemas */

export interface User {
  id: string
  email: string
  display_name: string | null
  age_gate_passed: boolean
  has_girlfriend: boolean
  current_girlfriend_id: string | null
}

/** Trait selection union types (exact values from onboarding). */
export type EmotionalStyle = "Caring" | "Playful" | "Reserved" | "Protective"
export type AttachmentStyle = "Very attached" | "Emotionally present" | "Calm but caring"
export type ReactionToAbsence = "High" | "Medium" | "Low"
export type CommunicationStyle = "Soft" | "Direct" | "Teasing"
export type RelationshipPace = "Slow" | "Natural" | "Fast"
export type CulturalPersonality = "Warm Slavic" | "Calm Central European" | "Passionate Balkan"

export interface TraitSelection {
  emotionalStyle: EmotionalStyle
  attachmentStyle: AttachmentStyle
  reactionToAbsence: ReactionToAbsence
  communicationStyle: CommunicationStyle
  relationshipPace: RelationshipPace
  culturalPersonality: CulturalPersonality
}

export interface Girlfriend {
  id: string
  display_name: string
  traits: TraitSelection
  created_at: string
}

/** Legacy alias for traits (snake_case from API). */
export interface Traits {
  emotional_style: string
  attachment_style: string
  reaction_to_absence: string
  communication_style: string
  relationship_pace: string
  cultural_personality: string
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
