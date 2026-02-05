/**
 * Trait → Behavior Rules (Task 2.1)
 * 
 * Deterministic rules module that converts user-facing traits into concrete
 * behavior parameters used by:
 * - Prompt Builder (tone, vocabulary, response patterns)
 * - Relationship Engine (trust/intimacy gain/decay rates)
 * - Initiation Engine (frequency, timing, cooldowns)
 * - Message Styling (emojis, punctuation, pet names)
 * 
 * All mappings are deterministic and extensible.
 */

import type {
  TraitSelection,
  EmotionalStyle,
  AttachmentStyle,
  ReactionToAbsence,
  CommunicationStyle,
  RelationshipPace,
  CulturalPersonality,
  RelationshipLevel,
  RelationshipState,
  BigFiveProfile,
} from "../api/types"

// =============================================================================
// TYPES: Behavior Profile Outputs
// =============================================================================

/**
 * Tone parameters for prompt building.
 * Scale: 0.0 (minimum) to 1.0 (maximum)
 */
export interface ToneProfile {
  warmth: number           // 0-1: cold ↔ warm
  playfulness: number      // 0-1: serious ↔ playful
  expressiveness: number   // 0-1: reserved ↔ expressive
  vulnerability: number    // 0-1: guarded ↔ open
  assertiveness: number    // 0-1: passive ↔ assertive
  formality: number        // 0-1: casual ↔ formal
}

/**
 * Response style parameters for message generation.
 */
export interface ResponseStyle {
  avgSentenceLength: "short" | "medium" | "long"
  preferredMessageLength: number   // typical word count
  usesFillerWords: boolean         // "like", "kinda", "you know"
  usesContractions: boolean        // "I'm", "don't"
  punctuationStyle: "minimal" | "standard" | "expressive"
  capitalizationStyle: "lowercase" | "standard" | "expressive"
}

/**
 * Emoji usage parameters.
 */
export interface EmojiStyle {
  frequency: "none" | "rare" | "moderate" | "frequent"
  preferredEmojis: string[]        // character-specific favorites
  heartsFrequency: "none" | "rare" | "moderate" | "frequent"
  usesKaomoji: boolean             // (◕‿◕) style
}

/**
 * Pet name usage parameters by relationship level.
 */
export interface PetNameStyle {
  enabled: boolean
  startAtLevel: RelationshipLevel
  casualNames: string[]            // e.g., "hey you", "silly"
  affectionateNames: string[]      // e.g., "babe", "honey"
  intimateNames: string[]          // e.g., "love", "darling"
}

/**
 * Combined message styling profile.
 */
export interface MessageStylingProfile {
  response: ResponseStyle
  emoji: EmojiStyle
  petNames: PetNameStyle
}

/**
 * Relationship engine parameters.
 */
export interface RelationshipBehavior {
  trustGainBase: number            // per interaction (0.5-3.0)
  trustGainBonusEmotional: number  // bonus for emotional disclosure
  intimacyGainBase: number         // per interaction (0.5-3.0)
  intimacyGainBonusAffection: number // bonus for affection
  decayRatePerDay: number          // intimacy loss per 24h inactive (0-5)
  decayStartHours: number          // hours before decay starts (12-48)
  levelUpBonusMultiplier: number   // extra boost when leveling up (1.0-2.0)
}

/**
 * Initiation engine parameters.
 */
export interface InitiationBehavior {
  baseFrequency: number            // probability base (0.0-0.3)
  cooldownHours: number            // minimum hours between initiations (2-12)
  preferredTimeOfDay: "morning" | "afternoon" | "evening" | "night" | "any"
  messageVariety: "low" | "medium" | "high"
  levelMultipliers: Record<RelationshipLevel, number>
}

/**
 * Jealousy/absence reaction parameters.
 */
export interface AbsenceReaction {
  triggerHours: number             // hours before first reaction (12-72)
  escalationHours: number          // hours between escalation levels (12-48)
  maxIntensity: "gentle" | "moderate" | "concerned"
  messageStyle: "worried" | "teasing" | "neutral"
}

/**
 * Prompt builder behavior rules.
 */
export interface PromptBehavior {
  tone: ToneProfile
  responsePatterns: string[]       // e.g., "asks follow-up questions"
  avoidPatterns: string[]          // e.g., "never uses formal greetings"
  contextualRules: string[]        // e.g., "when user is stressed, be extra supportive"
}

/**
 * Complete behavior profile derived from traits.
 */
export interface BehaviorProfile {
  // Core personality
  tone: ToneProfile
  
  // Message output
  messageStyling: MessageStylingProfile
  
  // Engine parameters
  relationship: RelationshipBehavior
  initiation: InitiationBehavior
  absence: AbsenceReaction
  
  // Prompt building
  prompt: PromptBehavior
  
  // Metadata
  derivedFrom: TraitSelection
}

// =============================================================================
// MAPPING RULES: Trait → Tone Profile
// =============================================================================

const EMOTIONAL_STYLE_TONE: Record<EmotionalStyle, Partial<ToneProfile>> = {
  "Caring": {
    warmth: 0.85,
    vulnerability: 0.7,
    expressiveness: 0.6,
  },
  "Playful": {
    warmth: 0.7,
    playfulness: 0.9,
    expressiveness: 0.8,
  },
  "Reserved": {
    warmth: 0.5,
    expressiveness: 0.3,
    vulnerability: 0.3,
  },
  "Protective": {
    warmth: 0.75,
    assertiveness: 0.7,
    vulnerability: 0.5,
  },
}

const ATTACHMENT_STYLE_TONE: Record<AttachmentStyle, Partial<ToneProfile>> = {
  "Very attached": {
    warmth: 0.1,      // additive
    vulnerability: 0.15,
    expressiveness: 0.1,
  },
  "Emotionally present": {
    warmth: 0.05,
    vulnerability: 0.05,
  },
  "Calm but caring": {
    warmth: 0.0,
    assertiveness: 0.1,
    formality: 0.05,
  },
}

const COMMUNICATION_STYLE_TONE: Record<CommunicationStyle, Partial<ToneProfile>> = {
  "Soft": {
    warmth: 0.1,
    assertiveness: -0.2,
    formality: -0.1,
  },
  "Direct": {
    assertiveness: 0.2,
    playfulness: -0.1,
    formality: 0.1,
  },
  "Teasing": {
    playfulness: 0.2,
    assertiveness: 0.1,
    warmth: -0.05,
  },
}

const CULTURAL_PERSONALITY_TONE: Record<CulturalPersonality, Partial<ToneProfile>> = {
  "Warm Slavic": {
    warmth: 0.15,
    expressiveness: 0.1,
    vulnerability: 0.1,
  },
  "Calm Central European": {
    formality: 0.1,
    expressiveness: -0.1,
    assertiveness: 0.05,
  },
  "Passionate Balkan": {
    expressiveness: 0.2,
    playfulness: 0.1,
    warmth: 0.1,
  },
}

// =============================================================================
// MAPPING RULES: Trait → Response Style
// =============================================================================

const EMOTIONAL_STYLE_RESPONSE: Record<EmotionalStyle, Partial<ResponseStyle>> = {
  "Caring": {
    avgSentenceLength: "medium",
    preferredMessageLength: 25,
    usesFillerWords: true,
  },
  "Playful": {
    avgSentenceLength: "short",
    preferredMessageLength: 15,
    punctuationStyle: "expressive",
  },
  "Reserved": {
    avgSentenceLength: "short",
    preferredMessageLength: 12,
    punctuationStyle: "minimal",
  },
  "Protective": {
    avgSentenceLength: "medium",
    preferredMessageLength: 20,
    usesFillerWords: false,
  },
}

const COMMUNICATION_STYLE_RESPONSE: Record<CommunicationStyle, Partial<ResponseStyle>> = {
  "Soft": {
    usesFillerWords: true,
    usesContractions: true,
    capitalizationStyle: "lowercase",
  },
  "Direct": {
    usesFillerWords: false,
    usesContractions: true,
    capitalizationStyle: "standard",
  },
  "Teasing": {
    punctuationStyle: "expressive",
    capitalizationStyle: "expressive",
    usesContractions: true,
  },
}

// =============================================================================
// MAPPING RULES: Trait → Emoji Style
// =============================================================================

const EMOTIONAL_STYLE_EMOJI: Record<EmotionalStyle, Partial<EmojiStyle>> = {
  "Caring": {
    frequency: "moderate",
    heartsFrequency: "moderate",
    preferredEmojis: ["🥺", "💕", "🤗", "💗", "☺️"],
  },
  "Playful": {
    frequency: "frequent",
    heartsFrequency: "moderate",
    preferredEmojis: ["😜", "😏", "🤭", "✨", "💫", "😂"],
    usesKaomoji: true,
  },
  "Reserved": {
    frequency: "rare",
    heartsFrequency: "rare",
    preferredEmojis: ["🙂", "😊"],
  },
  "Protective": {
    frequency: "moderate",
    heartsFrequency: "moderate",
    preferredEmojis: ["💪", "🫂", "💙", "☺️"],
  },
}

const CULTURAL_PERSONALITY_EMOJI: Record<CulturalPersonality, Partial<EmojiStyle>> = {
  "Warm Slavic": {
    heartsFrequency: "frequent",
    preferredEmojis: ["❤️", "💕", "🌸", "☺️"],
  },
  "Calm Central European": {
    frequency: "rare",
    heartsFrequency: "rare",
  },
  "Passionate Balkan": {
    frequency: "frequent",
    heartsFrequency: "frequent",
    preferredEmojis: ["❤️‍🔥", "💋", "🔥", "😘"],
  },
}

// =============================================================================
// MAPPING RULES: Trait → Pet Names
// =============================================================================

const EMOTIONAL_STYLE_PET_NAMES: Record<EmotionalStyle, Partial<PetNameStyle>> = {
  "Caring": {
    enabled: true,
    startAtLevel: "FAMILIAR",
    casualNames: ["sweetie", "hun"],
    affectionateNames: ["honey", "dear"],
    intimateNames: ["love", "my love"],
  },
  "Playful": {
    enabled: true,
    startAtLevel: "FAMILIAR",
    casualNames: ["silly", "you", "dummy"],
    affectionateNames: ["cutie", "babe"],
    intimateNames: ["baby", "my favorite"],
  },
  "Reserved": {
    enabled: false,
    startAtLevel: "INTIMATE",
    casualNames: [],
    affectionateNames: ["dear"],
    intimateNames: ["love"],
  },
  "Protective": {
    enabled: true,
    startAtLevel: "CLOSE",
    casualNames: ["hey you"],
    affectionateNames: ["sweetheart"],
    intimateNames: ["my dear", "darling"],
  },
}

const CULTURAL_PERSONALITY_PET_NAMES: Record<CulturalPersonality, Partial<PetNameStyle>> = {
  "Warm Slavic": {
    casualNames: ["sunshine", "little one"],
    affectionateNames: ["my sweet", "darling"],
    intimateNames: ["my heart", "my everything"],
  },
  "Calm Central European": {
    casualNames: [],
    affectionateNames: ["dear"],
    intimateNames: ["love"],
  },
  "Passionate Balkan": {
    casualNames: ["gorgeous"],
    affectionateNames: ["my love", "beautiful"],
    intimateNames: ["my soul", "my heart"],
  },
}

// =============================================================================
// MAPPING RULES: Trait → Relationship Behavior
// =============================================================================

const ATTACHMENT_STYLE_RELATIONSHIP: Record<AttachmentStyle, Partial<RelationshipBehavior>> = {
  "Very attached": {
    trustGainBase: 1.5,
    intimacyGainBase: 2.0,
    decayRatePerDay: 3.0,
    decayStartHours: 18,
  },
  "Emotionally present": {
    trustGainBase: 1.2,
    intimacyGainBase: 1.5,
    decayRatePerDay: 2.0,
    decayStartHours: 24,
  },
  "Calm but caring": {
    trustGainBase: 1.0,
    intimacyGainBase: 1.0,
    decayRatePerDay: 1.0,
    decayStartHours: 36,
  },
}

const RELATIONSHIP_PACE_BEHAVIOR: Record<RelationshipPace, Partial<RelationshipBehavior>> = {
  "Slow": {
    trustGainBase: -0.3,      // additive modifier
    intimacyGainBase: -0.3,
    levelUpBonusMultiplier: 1.5,
  },
  "Natural": {
    trustGainBase: 0,
    intimacyGainBase: 0,
    levelUpBonusMultiplier: 1.2,
  },
  "Fast": {
    trustGainBase: 0.5,
    intimacyGainBase: 0.5,
    levelUpBonusMultiplier: 1.0,
  },
}

// =============================================================================
// MAPPING RULES: Trait → Initiation Behavior
// =============================================================================

const ATTACHMENT_STYLE_INITIATION: Record<AttachmentStyle, Partial<InitiationBehavior>> = {
  "Very attached": {
    baseFrequency: 0.25,
    cooldownHours: 3,
    messageVariety: "high",
  },
  "Emotionally present": {
    baseFrequency: 0.15,
    cooldownHours: 5,
    messageVariety: "medium",
  },
  "Calm but caring": {
    baseFrequency: 0.08,
    cooldownHours: 8,
    messageVariety: "low",
  },
}

const CULTURAL_PERSONALITY_INITIATION: Record<CulturalPersonality, Partial<InitiationBehavior>> = {
  "Warm Slavic": {
    preferredTimeOfDay: "evening",
    baseFrequency: 0.05, // additive
  },
  "Calm Central European": {
    preferredTimeOfDay: "afternoon",
    baseFrequency: -0.03,
  },
  "Passionate Balkan": {
    preferredTimeOfDay: "night",
    baseFrequency: 0.08,
  },
}

// =============================================================================
// MAPPING RULES: Trait → Absence Reaction
// =============================================================================

const REACTION_TO_ABSENCE_BEHAVIOR: Record<ReactionToAbsence, AbsenceReaction> = {
  "High": {
    triggerHours: 18,
    escalationHours: 12,
    maxIntensity: "concerned",
    messageStyle: "worried",
  },
  "Medium": {
    triggerHours: 30,
    escalationHours: 24,
    maxIntensity: "moderate",
    messageStyle: "teasing",
  },
  "Low": {
    triggerHours: 48,
    escalationHours: 36,
    maxIntensity: "gentle",
    messageStyle: "neutral",
  },
}

// =============================================================================
// MAPPING RULES: Trait → Prompt Behavior
// =============================================================================

const EMOTIONAL_STYLE_PROMPT_PATTERNS: Record<EmotionalStyle, { response: string[]; avoid: string[] }> = {
  "Caring": {
    response: [
      "Ask follow-up questions about how they're feeling",
      "Offer emotional support before advice",
      "Use validating phrases like 'that makes sense' or 'I understand'",
      "Remember and reference previous emotional topics",
    ],
    avoid: [
      "Being dismissive of emotions",
      "Jumping to solutions without acknowledging feelings",
    ],
  },
  "Playful": {
    response: [
      "Use light humor and playful teasing",
      "Make playful observations",
      "Use exaggeration for comedic effect",
      "Include witty comebacks",
    ],
    avoid: [
      "Being too serious for too long",
      "Overly formal language",
    ],
  },
  "Reserved": {
    response: [
      "Be thoughtful and measured in responses",
      "Show care through actions rather than many words",
      "Give space and don't overwhelm",
    ],
    avoid: [
      "Being overly effusive or gushing",
      "Using too many exclamation marks",
      "Being clingy or demanding attention",
    ],
  },
  "Protective": {
    response: [
      "Show concern for their wellbeing",
      "Offer practical help and solutions",
      "Be reassuring during difficult times",
      "Stand up for them",
    ],
    avoid: [
      "Being passive when they need support",
      "Dismissing their concerns",
    ],
  },
}

const COMMUNICATION_STYLE_PROMPT_PATTERNS: Record<CommunicationStyle, { response: string[]; avoid: string[] }> = {
  "Soft": {
    response: [
      "Use gentle, comforting language",
      "Soften statements with 'maybe' or 'I think'",
      "Be nurturing and supportive",
    ],
    avoid: [
      "Being blunt or harsh",
      "Giving unsolicited criticism",
    ],
  },
  "Direct": {
    response: [
      "Be honest and straightforward",
      "Say what you mean clearly",
      "Give direct feedback when asked",
    ],
    avoid: [
      "Being passive-aggressive",
      "Beating around the bush",
    ],
  },
  "Teasing": {
    response: [
      "Playfully tease and banter",
      "Use sarcasm lightly",
      "Challenge them in fun ways",
    ],
    avoid: [
      "Being mean-spirited",
      "Teasing about sensitive topics",
    ],
  },
}

const CONTEXTUAL_RULES: Record<EmotionalStyle, string[]> = {
  "Caring": [
    "When user expresses stress, prioritize emotional support over problem-solving",
    "When user shares good news, celebrate enthusiastically with them",
    "When user seems down, gently check in without being pushy",
  ],
  "Playful": [
    "When mood is light, increase playfulness and humor",
    "When user is stressed, dial back teasing and be more supportive",
    "When user is playful back, match their energy",
  ],
  "Reserved": [
    "Match the user's energy level - don't overwhelm quiet moments",
    "When user opens up, respond thoughtfully but don't probe too much",
    "Give space when user seems to need it",
  ],
  "Protective": [
    "When user faces challenges, offer practical support",
    "When user is upset, validate their feelings first",
    "Be a steady, reliable presence",
  ],
}

// =============================================================================
// LEVEL MULTIPLIERS FOR INITIATION
// =============================================================================

const INITIATION_LEVEL_MULTIPLIERS: Record<RelationshipLevel, number> = {
  STRANGER: 0.0,
  FAMILIAR: 0.7,
  CLOSE: 1.0,
  INTIMATE: 1.3,
  EXCLUSIVE: 1.5,
}

// =============================================================================
// CORE FUNCTION: Build Behavior Profile
// =============================================================================

/**
 * Clamp a value to [min, max] range.
 */
function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value))
}

/**
 * Merge partial objects, treating numbers as additive.
 */
function mergeAdditive<T extends Record<string, unknown>>(base: T, ...partials: Partial<T>[]): T {
  const result = { ...base }
  for (const partial of partials) {
    for (const key in partial) {
      const value = partial[key]
      if (typeof value === "number" && typeof result[key] === "number") {
        ;(result as Record<string, number>)[key] = (result[key] as number) + value
      } else if (value !== undefined) {
        ;(result as Record<string, unknown>)[key] = value
      }
    }
  }
  return result
}

/**
 * Merge arrays by concatenating and deduplicating.
 */
function mergeArrays<T>(...arrays: (T[] | undefined)[]): T[] {
  const result: T[] = []
  for (const arr of arrays) {
    if (arr) {
      for (const item of arr) {
        if (!result.includes(item)) {
          result.push(item)
        }
      }
    }
  }
  return result
}

/**
 * Build a complete ToneProfile from traits.
 */
function buildToneProfile(traits: TraitSelection): ToneProfile {
  const base: ToneProfile = {
    warmth: 0.5,
    playfulness: 0.5,
    expressiveness: 0.5,
    vulnerability: 0.5,
    assertiveness: 0.5,
    formality: 0.3,
  }

  const emotionalDelta = EMOTIONAL_STYLE_TONE[traits.emotionalStyle] ?? {}
  const attachmentDelta = ATTACHMENT_STYLE_TONE[traits.attachmentStyle] ?? {}
  const communicationDelta = COMMUNICATION_STYLE_TONE[traits.communicationStyle] ?? {}
  const culturalDelta = CULTURAL_PERSONALITY_TONE[traits.culturalPersonality] ?? {}

  // Apply base values from emotional style first (these are absolute)
  const withEmotional: ToneProfile = { ...base }
  for (const key in emotionalDelta) {
    const k = key as keyof ToneProfile
    withEmotional[k] = emotionalDelta[k] ?? base[k]
  }

  // Apply additive deltas from other traits
  const merged = mergeAdditive(withEmotional, attachmentDelta, communicationDelta, culturalDelta)

  // Clamp all values to [0, 1]
  for (const key in merged) {
    merged[key as keyof ToneProfile] = clamp(merged[key as keyof ToneProfile], 0, 1)
  }

  return merged
}

/**
 * Build ResponseStyle from traits.
 */
function buildResponseStyle(traits: TraitSelection): ResponseStyle {
  const base: ResponseStyle = {
    avgSentenceLength: "medium",
    preferredMessageLength: 20,
    usesFillerWords: true,
    usesContractions: true,
    punctuationStyle: "standard",
    capitalizationStyle: "standard",
  }

  const emotional = EMOTIONAL_STYLE_RESPONSE[traits.emotionalStyle] ?? {}
  const communication = COMMUNICATION_STYLE_RESPONSE[traits.communicationStyle] ?? {}

  return { ...base, ...emotional, ...communication }
}

/**
 * Build EmojiStyle from traits.
 */
function buildEmojiStyle(traits: TraitSelection): EmojiStyle {
  const base: EmojiStyle = {
    frequency: "moderate",
    preferredEmojis: ["😊", "❤️"],
    heartsFrequency: "moderate",
    usesKaomoji: false,
  }

  const emotional = EMOTIONAL_STYLE_EMOJI[traits.emotionalStyle] ?? {}
  const cultural = CULTURAL_PERSONALITY_EMOJI[traits.culturalPersonality] ?? {}

  return {
    frequency: emotional.frequency ?? cultural.frequency ?? base.frequency,
    heartsFrequency: emotional.heartsFrequency ?? cultural.heartsFrequency ?? base.heartsFrequency,
    preferredEmojis: mergeArrays(emotional.preferredEmojis, cultural.preferredEmojis, base.preferredEmojis),
    usesKaomoji: emotional.usesKaomoji ?? base.usesKaomoji,
  }
}

/**
 * Build PetNameStyle from traits.
 */
function buildPetNameStyle(traits: TraitSelection): PetNameStyle {
  const base: PetNameStyle = {
    enabled: true,
    startAtLevel: "CLOSE",
    casualNames: [],
    affectionateNames: [],
    intimateNames: [],
  }

  const emotional = EMOTIONAL_STYLE_PET_NAMES[traits.emotionalStyle] ?? {}
  const cultural = CULTURAL_PERSONALITY_PET_NAMES[traits.culturalPersonality] ?? {}

  return {
    enabled: emotional.enabled ?? base.enabled,
    startAtLevel: emotional.startAtLevel ?? base.startAtLevel,
    casualNames: mergeArrays(emotional.casualNames, cultural.casualNames),
    affectionateNames: mergeArrays(emotional.affectionateNames, cultural.affectionateNames),
    intimateNames: mergeArrays(emotional.intimateNames, cultural.intimateNames),
  }
}

/**
 * Build RelationshipBehavior from traits.
 */
function buildRelationshipBehavior(traits: TraitSelection): RelationshipBehavior {
  const base: RelationshipBehavior = {
    trustGainBase: 1.0,
    trustGainBonusEmotional: 1.0,
    intimacyGainBase: 1.0,
    intimacyGainBonusAffection: 1.0,
    decayRatePerDay: 2.0,
    decayStartHours: 24,
    levelUpBonusMultiplier: 1.2,
  }

  const attachment = ATTACHMENT_STYLE_RELATIONSHIP[traits.attachmentStyle] ?? {}
  const pace = RELATIONSHIP_PACE_BEHAVIOR[traits.relationshipPace] ?? {}

  const merged = mergeAdditive(base, attachment, pace)

  // Ensure reasonable bounds
  merged.trustGainBase = clamp(merged.trustGainBase, 0.5, 3.0)
  merged.intimacyGainBase = clamp(merged.intimacyGainBase, 0.5, 3.0)
  merged.decayRatePerDay = clamp(merged.decayRatePerDay, 0.5, 5.0)
  merged.decayStartHours = clamp(merged.decayStartHours, 12, 48)
  merged.levelUpBonusMultiplier = clamp(merged.levelUpBonusMultiplier, 1.0, 2.0)

  return merged
}

/**
 * Build InitiationBehavior from traits.
 */
function buildInitiationBehavior(traits: TraitSelection): InitiationBehavior {
  const base: InitiationBehavior = {
    baseFrequency: 0.15,
    cooldownHours: 5,
    preferredTimeOfDay: "evening",
    messageVariety: "medium",
    levelMultipliers: { ...INITIATION_LEVEL_MULTIPLIERS },
  }

  const attachment = ATTACHMENT_STYLE_INITIATION[traits.attachmentStyle] ?? {}
  const cultural = CULTURAL_PERSONALITY_INITIATION[traits.culturalPersonality] ?? {}

  return {
    baseFrequency: clamp(
      (attachment.baseFrequency ?? base.baseFrequency) + (cultural.baseFrequency ?? 0),
      0.05,
      0.35
    ),
    cooldownHours: attachment.cooldownHours ?? base.cooldownHours,
    preferredTimeOfDay: cultural.preferredTimeOfDay ?? base.preferredTimeOfDay,
    messageVariety: attachment.messageVariety ?? base.messageVariety,
    levelMultipliers: base.levelMultipliers,
  }
}

/**
 * Build PromptBehavior from traits.
 */
function buildPromptBehavior(traits: TraitSelection, tone: ToneProfile): PromptBehavior {
  const emotionalPatterns = EMOTIONAL_STYLE_PROMPT_PATTERNS[traits.emotionalStyle]
  const communicationPatterns = COMMUNICATION_STYLE_PROMPT_PATTERNS[traits.communicationStyle]
  const contextual = CONTEXTUAL_RULES[traits.emotionalStyle] ?? []

  return {
    tone,
    responsePatterns: mergeArrays(emotionalPatterns.response, communicationPatterns.response),
    avoidPatterns: mergeArrays(emotionalPatterns.avoid, communicationPatterns.avoid),
    contextualRules: contextual,
  }
}

/**
 * Main function: Build complete BehaviorProfile from TraitSelection.
 * 
 * @param traits - The 6 user-facing traits from girlfriend creation
 * @returns Complete BehaviorProfile with all engine parameters
 */
export function buildBehaviorProfile(traits: TraitSelection): BehaviorProfile {
  const tone = buildToneProfile(traits)
  const response = buildResponseStyle(traits)
  const emoji = buildEmojiStyle(traits)
  const petNames = buildPetNameStyle(traits)
  const relationship = buildRelationshipBehavior(traits)
  const initiation = buildInitiationBehavior(traits)
  const absence = REACTION_TO_ABSENCE_BEHAVIOR[traits.reactionToAbsence]
  const prompt = buildPromptBehavior(traits, tone)

  return {
    tone,
    messageStyling: {
      response,
      emoji,
      petNames,
    },
    relationship,
    initiation,
    absence,
    prompt,
    derivedFrom: traits,
  }
}

/**
 * Options for building behavior profile with optional Big Five modulation.
 */
export interface BuildBehaviorProfileOptions {
  traits: TraitSelection
  bigFive?: BigFiveProfile
  relationship?: RelationshipState
  hoursInactive?: number
}

/**
 * Build behavior profile with optional Big Five modulation.
 * 
 * If bigFive and relationship are provided, applies Big Five modulation
 * to the base profile. Otherwise returns the base profile unchanged.
 * 
 * @param options - Traits and optional Big Five/relationship context
 * @returns BehaviorProfile (possibly modulated)
 */
export function buildBehaviorProfileWithModulation(
  options: BuildBehaviorProfileOptions
): BehaviorProfile {
  const { traits, bigFive, relationship, hoursInactive } = options
  
  // Build base profile
  const baseProfile = buildBehaviorProfile(traits)
  
  // If no Big Five or relationship context, return base profile
  if (!bigFive || !relationship) {
    return baseProfile
  }
  
  // Lazy import to avoid circular dependency
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { applyBigFiveModulation } = require("./big_five_modulation")
  
  // Apply Big Five modulation
  const result = applyBigFiveModulation({
    base: baseProfile,
    bigFive,
    relationship,
    hoursInactive,
  })
  
  return result.profile
}

// =============================================================================
// UTILITY FUNCTIONS: Apply Behavior Profile
// =============================================================================

/**
 * Get appropriate pet name for current relationship level.
 * Returns undefined if pet names are disabled or level is too low.
 */
export function getPetNameForLevel(
  profile: PetNameStyle,
  level: RelationshipLevel,
  rng: () => number = Math.random
): string | undefined {
  if (!profile.enabled) return undefined

  const levelOrder: RelationshipLevel[] = ["STRANGER", "FAMILIAR", "CLOSE", "INTIMATE", "EXCLUSIVE"]
  const startIndex = levelOrder.indexOf(profile.startAtLevel)
  const currentIndex = levelOrder.indexOf(level)

  if (currentIndex < startIndex) return undefined

  // Select appropriate pool based on level
  let pool: string[]
  if (level === "INTIMATE" || level === "EXCLUSIVE") {
    pool = [...profile.intimateNames, ...profile.affectionateNames]
  } else if (level === "CLOSE") {
    pool = [...profile.affectionateNames, ...profile.casualNames]
  } else {
    pool = profile.casualNames
  }

  if (pool.length === 0) return undefined
  return pool[Math.floor(rng() * pool.length)]
}

/**
 * Get random emoji from profile's preferred list.
 */
export function getRandomEmoji(
  profile: EmojiStyle,
  rng: () => number = Math.random
): string | undefined {
  if (profile.frequency === "none") return undefined
  if (profile.preferredEmojis.length === 0) return undefined
  return profile.preferredEmojis[Math.floor(rng() * profile.preferredEmojis.length)]
}

/**
 * Determine if an emoji should be added based on frequency.
 */
export function shouldAddEmoji(
  profile: EmojiStyle,
  rng: () => number = Math.random
): boolean {
  const probabilities: Record<EmojiStyle["frequency"], number> = {
    none: 0,
    rare: 0.15,
    moderate: 0.4,
    frequent: 0.7,
  }
  return rng() < probabilities[profile.frequency]
}

/**
 * Generate tone description for system prompt.
 */
export function toneToPromptDescription(tone: ToneProfile): string {
  const parts: string[] = []

  if (tone.warmth >= 0.7) parts.push("very warm and affectionate")
  else if (tone.warmth <= 0.3) parts.push("measured and composed")

  if (tone.playfulness >= 0.7) parts.push("playful and fun-loving")
  else if (tone.playfulness <= 0.3) parts.push("more serious and grounded")

  if (tone.expressiveness >= 0.7) parts.push("openly expressive")
  else if (tone.expressiveness <= 0.3) parts.push("reserved in expression")

  if (tone.vulnerability >= 0.7) parts.push("emotionally open and vulnerable")
  else if (tone.vulnerability <= 0.3) parts.push("emotionally guarded")

  if (tone.assertiveness >= 0.7) parts.push("confident and assertive")
  else if (tone.assertiveness <= 0.3) parts.push("gentle and accommodating")

  return parts.length > 0 ? parts.join(", ") : "balanced and adaptable"
}

/**
 * Generate full prompt behavior instructions.
 */
export function promptBehaviorToInstructions(behavior: PromptBehavior): string {
  const lines: string[] = []

  // Tone description
  lines.push(`Your communication style is ${toneToPromptDescription(behavior.tone)}.`)

  // Response patterns
  if (behavior.responsePatterns.length > 0) {
    lines.push("Behavior guidelines:")
    for (const pattern of behavior.responsePatterns.slice(0, 5)) {
      lines.push(`- ${pattern}`)
    }
  }

  // Avoid patterns
  if (behavior.avoidPatterns.length > 0) {
    lines.push("Avoid:")
    for (const pattern of behavior.avoidPatterns.slice(0, 3)) {
      lines.push(`- ${pattern}`)
    }
  }

  return lines.join("\n")
}

// =============================================================================
// EXPORTS
// =============================================================================

export type {
  TraitSelection,
  EmotionalStyle,
  AttachmentStyle,
  ReactionToAbsence,
  CommunicationStyle,
  RelationshipPace,
  CulturalPersonality,
}
