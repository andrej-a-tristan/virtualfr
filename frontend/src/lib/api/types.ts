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

export type AppearancePrefs = {
  vibe?:
    | "cute"
    | "elegant"
    | "sporty"
    | "goth"
    | "girl-next-door"
    | "model"
  age_range?: "18" | "19-21" | "22-26" | "27+"
  ethnicity?:
    | "any"
    | "asian"
    | "black"
    | "latina"
    | "white"
    | "middle-eastern"
    | "south-asian"
  breast_size?: "small" | "medium" | "large" | "massive"
  butt_size?: "small" | "medium" | "large" | "massive"
  hair_color?: "black" | "brown" | "blonde" | "red" | "ginger" | "unnatural"
  hair_style?: "long" | "bob" | "curly" | "straight" | "bun"
  eye_color?: "brown" | "blue" | "green" | "hazel"
  body_type?: "slim" | "athletic" | "curvy"
}

export type ContentPrefs = { wants_spicy_photos: boolean }

export type IdentityPrefs = {
  girlfriend_name: string
  job_vibe?: string
  hobbies: string[]
  origin_vibe?: string
}

export type IdentityCanon = {
  backstory: string
  daily_routine: string
  favorites: {
    music_vibe: string
    comfort_food: string
    weekend_idea: string
  }
  memory_seeds: string[]
}

export type OnboardingCompleteRequest = {
  traits: Traits
  appearance_prefs: AppearancePrefs
  content_prefs: ContentPrefs
  identity: IdentityPrefs
}

export interface Girlfriend {
  id: string
  display_name?: string
  name?: string
  avatar_url?: string | null
  traits: TraitSelection | Traits
  appearance_prefs?: Record<string, any>
  content_prefs?: Record<string, any>
  identity?: IdentityPrefs
  identity_canon?: IdentityCanon
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

export type Plan = "free" | "plus" | "premium"

export interface BillingStatus {
  plan: Plan
  has_card_on_file: boolean
  message_cap: number
  image_cap: number
  girls_max: number
  girls_count: number
  can_create_more_girls: boolean
  current_period_end: string | null
  next_renewal_date: string | null
  next_invoice_amount: number | null
  subscription_status: string | null
}

// ── Plan change (proration) types ─────────────────────────────────────────

export interface ProrationLineItem {
  description: string
  amount: number // cents
  currency: string
}

export interface InvoiceSummary {
  amount_due: number // cents
  currency: string
  paid: boolean
  hosted_invoice_url?: string | null
}

export interface PreviewPlanChangeResponse {
  amount_due_now: number // cents
  currency: string
  next_recurring_amount: number // cents
  next_renewal_date: string
  proration_line_items: ProrationLineItem[]
}

export interface ChangePlanResponse {
  ok: boolean
  plan: Plan
  previous_plan: Plan
  subscription_id: string | null
  current_period_end: string | null
  invoice?: InvoiceSummary | null
}

// Multi-girl
export interface GirlfriendListResponse {
  girlfriends: Girlfriend[]
  current_girlfriend_id: string | null
  girls_max: number
  can_create_more: boolean
}

export interface SetCurrentGirlfriendRequest {
  girlfriend_id: string
}

export interface SwitchGirlfriendResponse {
  girlfriends: Girlfriend[]
  current_girlfriend_id: string
}

export interface CreateGirlfriendResponse {
  girlfriend: Girlfriend
  girlfriends: Girlfriend[]
  current_girlfriend_id: string
}

export interface SetupIntentResponse {
  client_secret: string
  publishable_key: string
}

// -----------------------------------------------------------------------------
// Payment Method
// -----------------------------------------------------------------------------

export interface PaymentMethodCardSummary {
  brand: string
  last4: string
  exp_month: number
  exp_year: number
}

export interface PaymentMethodResponse {
  has_card: boolean
  card: PaymentMethodCardSummary | null
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

// -----------------------------------------------------------------------------
// Gift System
// -----------------------------------------------------------------------------

export interface GiftImageReward {
  album_size: number
  prompt_template: string
  suggestive_level: string
}

export interface GiftRelationshipBoost {
  trust: number
  intimacy: number
}

export interface GiftDefinition {
  id: string
  name: string
  description: string
  price_eur: number
  tier: "everyday" | "dates" | "luxury" | "legendary"
  relationship_boost: GiftRelationshipBoost
  memory_tag: string
  image_reward: GiftImageReward
  cooldown_days: number | null
  rarity: "common" | "rare" | "legendary"
  emoji: string
  unique_effect_name: string
  unique_effect_description: string
}

export interface GiftListResponse {
  gifts: GiftDefinition[]
}

export interface GiftCheckoutResponse {
  status: "succeeded" | "requires_action" | "failed" | "no_card"
  client_secret?: string
  payment_intent_id?: string
  error?: string
}

export interface GiftHistoryItem {
  id: string
  gift_id: string
  gift_name: string
  amount_eur: number
  status: "pending" | "paid" | "failed"
  created_at: string
  emoji: string
}

export interface GiftHistoryResponse {
  purchases: GiftHistoryItem[]
}

export interface GiftEventData {
  gift_id: string
  gift_name: string
  emoji: string
  tier: string
  trust_gained: number
  intimacy_gained: number
  unique_effect_name: string
  unique_effect_description: string
}
