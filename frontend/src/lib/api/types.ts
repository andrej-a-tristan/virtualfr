/** API types aligned with backend schemas */

export interface User {
  id: string
  email: string
  display_name: string | null
  age_gate_passed: boolean
  has_girlfriend: boolean
  current_girlfriend_id: string | null
  language_pref?: string // e.g. "en" | "sk"; TODO: wrap outputs in Slovak if "sk"
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
  event_key?: string | null
  created_at: string
}

/** Relationship level (matches backend + engines). */
export type RelationshipLevel =
  | "STRANGER"
  | "FAMILIAR"
  | "CLOSE"
  | "INTIMATE"
  | "EXCLUSIVE"

export interface RelationshipState {
  trust: number
  intimacy: number
  level: RelationshipLevel
  last_interaction_at: string | null
  milestones_reached?: RelationshipLevel[]
}

export interface UserHabitProfile {
  preferred_hours?: number[]
  typical_gap_hours?: number | null
  updated_at?: string
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

// -----------------------------------------------------------------------------
// Memory System Types (Task 1.2)
// -----------------------------------------------------------------------------

export type MemoryType = "factual" | "emotional"

/** A stable fact about the user. */
export interface FactualMemoryItem {
  id: string
  key: string                    // e.g. "user.name", "user.city", "pref.music"
  value: string
  confidence: number             // 0-100
  first_seen_at: string
  last_seen_at: string
  source_message_id: string | null
}

/** An emotional event/feeling. */
export interface EmotionalMemoryItem {
  id: string
  event: string                  // short summary
  emotion_tags: string[]         // e.g. ["stress", "anxiety"]
  valence: number                // -5 to +5
  intensity: number              // 1-5
  occurred_at: string
  source_message_id: string | null
}

/** Compact memory context for prompt building. */
export interface MemoryContext {
  facts: string[]                // Human-readable fact summaries
  emotions: string[]             // Human-readable emotion summaries
  habits: string[]               // Optional habit hints
}

/** Memory stats/summary response. */
export interface MemorySummary {
  factual_count: number
  emotional_count: number
  recent_facts: Array<{ key: string; value: string }>
  recent_emotions: Array<{ event: string; tags: string[] }>
}

/** Memory items list response. */
export interface MemoryItemsResponse<T> {
  type: MemoryType
  count: number
  items: T[]
}

// -----------------------------------------------------------------------------
// Big Five Personality Types (Task 2.2)
// -----------------------------------------------------------------------------

/** Big Five personality values (0-100 scale). */
export interface BigFive {
  openness: number           // 0-100: conventional ↔ creative/curious
  conscientiousness: number  // 0-100: spontaneous ↔ organized/reliable
  extraversion: number       // 0-100: introverted ↔ outgoing/expressive
  agreeableness: number      // 0-100: independent ↔ warm/trusting
  neuroticism: number        // 0-100: stable ↔ emotionally sensitive
}

/** Source of Big Five values. */
export type BigFiveSource = "base" | "trait_mapped"

/** Big Five profile with source tracking. */
export interface BigFiveProfile {
  values: BigFive
  source: BigFiveSource
}
