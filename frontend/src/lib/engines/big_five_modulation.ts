/**
 * Big Five Behavior Modulation (Task 2.2)
 * 
 * Deterministic module that takes Big Five personality values and modulates
 * the BehaviorProfile from Task 2.1. Affects:
 * - Emotional intensity (warmth, expressiveness, emoji usage)
 * - Anxiety/reassurance (absence reactions, check-in behavior)
 * - Message length and structure
 * - Initiative frequency and timing
 * 
 * All modulation is deterministic with no randomness.
 * No guilt/pressure language is ever introduced.
 */

import type {
  BigFive,
  BigFiveProfile,
  RelationshipLevel,
  RelationshipState,
} from "../api/types"

import type {
  BehaviorProfile,
  ToneProfile,
  ResponseStyle,
  EmojiStyle,
  InitiationBehavior,
  AbsenceReaction,
} from "./trait_behavior_rules"

// Re-export types for convenience
export type { BigFive, BigFiveProfile }

// =============================================================================
// EXTENDED TYPES FOR MODULATION
// =============================================================================

/**
 * Extended behavior parameters added by Big Five modulation.
 * These complement the base BehaviorProfile.
 */
export interface ModulatedBehaviorExtensions {
  // Affection parameters (0-3 scale)
  affection: {
    reassuranceLevel: number      // 1-3: how much reassurance to provide
    checkInFrequency: number      // 0-3: how often to check in
    protectiveness: number        // 0-3: protective behavior intensity
  }
  
  // Phrasing parameters
  phrasing: {
    emojiRate: number             // 0-3: emoji frequency boost
    directness: number            // 1-3: how direct in communication
    teasingLevel: number          // 0-3: playful teasing intensity
    flirtiness: number            // 0-3: flirtatious behavior level
  }
  
  // Extended initiation parameters
  initiationExt: {
    probabilityBoost: number      // 0.00-0.12: added to base frequency
    minIntimacyToInitiate: number // 10-35: minimum intimacy to initiate
  }
}

/**
 * Modulated behavior profile with extensions.
 */
export interface ModulatedBehaviorProfile extends BehaviorProfile {
  extensions: ModulatedBehaviorExtensions
  modulationApplied: boolean
}

/**
 * Result of Big Five modulation.
 */
export interface ModulationResult {
  profile: ModulatedBehaviorProfile
  notes: string[]
}

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

/**
 * Clamp a number to [min, max] range.
 */
export function clamp(num: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, num))
}

/**
 * Normalize 0-100 value to 0-1 range.
 */
export function normalize100(x: number): number {
  return clamp(x, 0, 100) / 100
}

/**
 * Convert 0-100 value to centered -1 to +1 range.
 * Formula: (x - 50) / 25, clamped to [-1, 1]
 * - 0 → -2 (clamped to -1)
 * - 25 → -1
 * - 50 → 0
 * - 75 → +1
 * - 100 → +2 (clamped to +1)
 */
export function z(x: number): number {
  return clamp((x - 50) / 25, -1, 1)
}

/**
 * Step sentence length up or down.
 */
function stepSentenceLength(
  current: "short" | "medium" | "long",
  direction: "up" | "down"
): "short" | "medium" | "long" {
  const order: Array<"short" | "medium" | "long"> = ["short", "medium", "long"]
  const idx = order.indexOf(current)
  if (direction === "up") {
    return order[Math.min(idx + 1, 2)]
  } else {
    return order[Math.max(idx - 1, 0)]
  }
}

/**
 * Map emoji frequency string to numeric rate (0-3).
 */
function emojiFrequencyToRate(freq: EmojiStyle["frequency"]): number {
  const map: Record<EmojiStyle["frequency"], number> = {
    none: 0,
    rare: 1,
    moderate: 2,
    frequent: 3,
  }
  return map[freq]
}

/**
 * Map numeric rate (0-3) to emoji frequency string.
 */
function rateToEmojiFrequency(rate: number): EmojiStyle["frequency"] {
  const clamped = clamp(Math.round(rate), 0, 3)
  const map: EmojiStyle["frequency"][] = ["none", "rare", "moderate", "frequent"]
  return map[clamped]
}

/**
 * Map absence reaction intensity string to numeric (1-3).
 */
function intensityToNumber(intensity: AbsenceReaction["maxIntensity"]): number {
  const map: Record<AbsenceReaction["maxIntensity"], number> = {
    gentle: 1,
    moderate: 2,
    concerned: 3,
  }
  return map[intensity]
}

/**
 * Map numeric (1-3) to absence reaction intensity string.
 */
function numberToIntensity(num: number): AbsenceReaction["maxIntensity"] {
  const clamped = clamp(Math.round(num), 1, 3)
  const map: AbsenceReaction["maxIntensity"][] = ["gentle", "moderate", "concerned"]
  return map[clamped - 1]
}

/**
 * Get relationship level order index (0-4).
 */
function levelIndex(level: RelationshipLevel): number {
  const order: RelationshipLevel[] = ["STRANGER", "FAMILIAR", "CLOSE", "INTIMATE", "EXCLUSIVE"]
  return order.indexOf(level)
}

/**
 * Deep clone an object.
 */
function deepClone<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj))
}

// =============================================================================
// DEFAULT EXTENSIONS
// =============================================================================

/**
 * Create default modulation extensions based on base profile.
 */
function createDefaultExtensions(base: BehaviorProfile): ModulatedBehaviorExtensions {
  // Derive initial values from base profile
  const emojiRate = emojiFrequencyToRate(base.messageStyling.emoji.frequency)
  
  // Directness from tone assertiveness
  const directness = base.tone.assertiveness >= 0.7 ? 3 : base.tone.assertiveness >= 0.4 ? 2 : 1
  
  // Teasing from playfulness
  const teasingLevel = base.tone.playfulness >= 0.7 ? 2 : base.tone.playfulness >= 0.5 ? 1 : 0
  
  // Flirtiness starts conservative
  const flirtiness = base.tone.warmth >= 0.7 ? 1 : 0
  
  // Reassurance from warmth + vulnerability
  const reassuranceLevel = base.tone.warmth >= 0.7 ? 2 : 1
  
  // Check-in frequency from attachment behavior
  const checkInFrequency = base.initiation.baseFrequency >= 0.2 ? 2 : 1
  
  // Protectiveness from assertiveness
  const protectiveness = base.tone.assertiveness >= 0.6 ? 2 : 1
  
  return {
    affection: {
      reassuranceLevel: clamp(reassuranceLevel, 1, 3),
      checkInFrequency: clamp(checkInFrequency, 0, 3),
      protectiveness: clamp(protectiveness, 0, 3),
    },
    phrasing: {
      emojiRate: clamp(emojiRate, 0, 3),
      directness: clamp(directness, 1, 3),
      teasingLevel: clamp(teasingLevel, 0, 3),
      flirtiness: clamp(flirtiness, 0, 3),
    },
    initiationExt: {
      probabilityBoost: 0,
      minIntimacyToInitiate: 20, // Default minimum intimacy
    },
  }
}

// =============================================================================
// MAIN MODULATION FUNCTION
// =============================================================================

export interface ApplyBigFiveModulationParams {
  base: BehaviorProfile
  bigFive: BigFiveProfile
  relationship: RelationshipState
  hoursInactive?: number
}

/**
 * Apply Big Five modulation to a base BehaviorProfile.
 * 
 * @param params - Base profile, Big Five values, relationship state, optional hours inactive
 * @returns Modulated profile with same shape + extension fields + debug notes
 */
export function applyBigFiveModulation(
  params: ApplyBigFiveModulationParams
): ModulationResult {
  const { base, bigFive, relationship, hoursInactive = 0 } = params
  const notes: string[] = []
  
  // Deep clone base to avoid mutations
  const profile = deepClone(base) as ModulatedBehaviorProfile
  
  // Initialize extensions
  const ext = createDefaultExtensions(base)
  
  // Extract Big Five z-scores
  const E = z(bigFive.values.extraversion)
  const A = z(bigFive.values.agreeableness)
  const N = z(bigFive.values.neuroticism)
  const C = z(bigFive.values.conscientiousness)
  const O = z(bigFive.values.openness)
  
  // Track original values for notes
  const origEmoji = ext.phrasing.emojiRate
  const origReassurance = ext.affection.reassuranceLevel
  
  // =========================================================================
  // A) EMOTIONAL INTENSITY (affection + expressiveness)
  // =========================================================================
  
  // Reassurance level: A*0.6 + N*0.4
  const reassuranceDelta = Math.round(A * 0.6 + N * 0.4)
  ext.affection.reassuranceLevel = clamp(ext.affection.reassuranceLevel + reassuranceDelta, 1, 3)
  
  // Emoji rate: E*0.6 + A*0.3 - C*0.2
  const emojiDelta = Math.round(E * 0.6 + A * 0.3 - C * 0.2)
  ext.phrasing.emojiRate = clamp(ext.phrasing.emojiRate + emojiDelta, 0, 3)
  
  // Update emoji frequency in profile
  profile.messageStyling.emoji.frequency = rateToEmojiFrequency(ext.phrasing.emojiRate)
  
  // Sentence length: step based on E + O
  const eoSum = E + O
  if (eoSum > 0.8) {
    profile.messageStyling.response.avgSentenceLength = stepSentenceLength(
      profile.messageStyling.response.avgSentenceLength,
      "up"
    )
    notes.push("High extraversion+openness increased message length")
  } else if (eoSum < -0.8) {
    profile.messageStyling.response.avgSentenceLength = stepSentenceLength(
      profile.messageStyling.response.avgSentenceLength,
      "down"
    )
    notes.push("Low extraversion+openness decreased message length")
  }
  
  // Check-in frequency: A*0.5 + E*0.3 - C*0.2
  const checkInDelta = Math.round(A * 0.5 + E * 0.3 - C * 0.2)
  ext.affection.checkInFrequency = clamp(ext.affection.checkInFrequency + checkInDelta, 0, 3)
  
  // Update tone expressiveness based on E
  if (E > 0.5) {
    profile.tone.expressiveness = clamp(profile.tone.expressiveness + 0.15, 0, 1)
  }
  
  // =========================================================================
  // B) ANXIETY / REASSURANCE (no guilt, no spam)
  // =========================================================================
  
  // High neuroticism (N > 0.8)
  if (N > 0.8) {
    // Change absence reaction style to calm check-in
    // Unless already "worried" AND relationship is INTIMATE+
    const isIntimate = levelIndex(relationship.level) >= levelIndex("INTIMATE")
    if (!(profile.absence.messageStyle === "worried" && isIntimate)) {
      profile.absence.messageStyle = "neutral" // "calm_checkin" mapped to neutral
      notes.push("High neuroticism softened absence reaction style")
    }
    
    // Increase intensity but NOT frequency
    const currentIntensity = intensityToNumber(profile.absence.maxIntensity)
    profile.absence.maxIntensity = numberToIntensity(currentIntensity + 1)
    
    // Softer phrasing: reduce directness if not already "direct" communication style
    if (base.derivedFrom.communicationStyle !== "Direct") {
      ext.phrasing.directness = clamp(ext.phrasing.directness - 1, 1, 3)
    }
  }
  
  // High conscientiousness (C > 0.8)
  if (C > 0.8) {
    // Reduce absence intensity (more composed)
    const currentIntensity = intensityToNumber(profile.absence.maxIntensity)
    profile.absence.maxIntensity = numberToIntensity(currentIntensity - 1)
    
    // Reduce protectiveness unless base emotional style is "Protective"
    if (base.derivedFrom.emotionalStyle !== "Protective") {
      ext.affection.protectiveness = clamp(ext.affection.protectiveness - 1, 0, 3)
    }
    
    notes.push("High conscientiousness increased composure")
  }
  
  // =========================================================================
  // C) INITIATIVE FREQUENCY (healthy, no spam)
  // =========================================================================
  
  // Probability boost: E*0.04 + A*0.02, clamped to [-0.02, 0.08]
  // IMPORTANT: N does NOT affect probability, only style
  const probBoost = clamp(E * 0.04 + A * 0.02, -0.02, 0.08)
  ext.initiationExt.probabilityBoost = clamp(probBoost, 0, 0.12)
  
  // Cooldown hours: reduced by E (higher E = shorter cooldown)
  const cooldownDelta = Math.round(E * 1.2)
  profile.initiation.cooldownHours = clamp(
    profile.initiation.cooldownHours - cooldownDelta,
    3,
    12
  )
  
  // Min intimacy to initiate: reduced by E (higher E initiates earlier)
  const intimacyDelta = Math.round(E * 4)
  ext.initiationExt.minIntimacyToInitiate = clamp(
    ext.initiationExt.minIntimacyToInitiate - intimacyDelta,
    10,
    35
  )
  
  // Apply probability boost to base frequency
  profile.initiation.baseFrequency = clamp(
    profile.initiation.baseFrequency + ext.initiationExt.probabilityBoost,
    0,
    0.35
  )
  
  if (E > 0.5) {
    notes.push("High extraversion increased initiation frequency")
  }
  
  // =========================================================================
  // D) VARIETY / NOVELTY (openness)
  // =========================================================================
  
  if (O > 0.8) {
    // Increase teasing if base allows
    if (
      base.derivedFrom.communicationStyle === "Teasing" ||
      base.derivedFrom.emotionalStyle === "Playful"
    ) {
      ext.phrasing.teasingLevel = clamp(ext.phrasing.teasingLevel + 1, 0, 3)
      notes.push("High openness increased playful variety")
    }
  } else if (O < -0.8) {
    // Reduce teasing, prefer simpler messages
    ext.phrasing.teasingLevel = clamp(ext.phrasing.teasingLevel - 1, 0, 3)
    
    // Cap sentence length at medium unless EXCLUSIVE
    if (
      relationship.level !== "EXCLUSIVE" &&
      profile.messageStyling.response.avgSentenceLength === "long"
    ) {
      profile.messageStyling.response.avgSentenceLength = "medium"
    }
  }
  
  // =========================================================================
  // E) STEADINESS / STRUCTURE (conscientiousness)
  // =========================================================================
  
  if (C > 0.8) {
    // Tend toward medium sentence length (not long)
    // Unless soft communication and INTIMATE+
    const isSoftIntimate =
      base.derivedFrom.communicationStyle === "Soft" &&
      levelIndex(relationship.level) >= levelIndex("INTIMATE")
    
    if (!isSoftIntimate && profile.messageStyling.response.avgSentenceLength === "long") {
      profile.messageStyling.response.avgSentenceLength = "medium"
    }
    
    // Increase directness if already direct
    if (base.derivedFrom.communicationStyle === "Direct") {
      ext.phrasing.directness = clamp(ext.phrasing.directness + 1, 1, 3)
    }
    
    // Reduce emoji rate if > 1
    if (ext.phrasing.emojiRate > 1) {
      ext.phrasing.emojiRate = clamp(ext.phrasing.emojiRate - 1, 0, 3)
      profile.messageStyling.emoji.frequency = rateToEmojiFrequency(ext.phrasing.emojiRate)
    }
  }
  
  // =========================================================================
  // RELATIONSHIP-LEVEL GATING (final pass)
  // =========================================================================
  
  if (relationship.level === "STRANGER") {
    // Enforce conservative settings for strangers
    ext.initiationExt.probabilityBoost = 0
    profile.initiation.baseFrequency = base.initiation.baseFrequency // Reset boost
    profile.initiation.cooldownHours = Math.max(profile.initiation.cooldownHours, 8)
    profile.messageStyling.petNames.enabled = false
    ext.phrasing.flirtiness = Math.min(ext.phrasing.flirtiness, 1)
    
    notes.push("Stranger level: conservative initiation enforced")
  }
  
  // Pace-based flirtiness caps
  if (base.derivedFrom.relationshipPace === "Slow") {
    const maxFlirtinessAtLevel: Record<RelationshipLevel, number> = {
      STRANGER: 0,
      FAMILIAR: 1,
      CLOSE: 1,
      INTIMATE: 2,
      EXCLUSIVE: 3,
    }
    const cap = maxFlirtinessAtLevel[relationship.level]
    ext.phrasing.flirtiness = Math.min(ext.phrasing.flirtiness, cap)
  }
  
  // =========================================================================
  // ADD SUMMARY NOTES
  // =========================================================================
  
  // Only add delta notes if significant changes occurred
  if (ext.phrasing.emojiRate !== origEmoji) {
    if (ext.phrasing.emojiRate > origEmoji) {
      notes.push("Big Five increased emoji usage")
    } else {
      notes.push("Big Five decreased emoji usage")
    }
  }
  
  if (ext.affection.reassuranceLevel !== origReassurance) {
    if (ext.affection.reassuranceLevel > origReassurance) {
      notes.push("Big Five increased reassurance behavior")
    }
  }
  
  // Limit notes to 6 max
  const finalNotes = notes.slice(0, 6)
  
  // =========================================================================
  // ASSEMBLE FINAL PROFILE
  // =========================================================================
  
  profile.extensions = ext
  profile.modulationApplied = true
  
  return {
    profile,
    notes: finalNotes,
  }
}

// =============================================================================
// UTILITY: CHECK IF PROFILE HAS MODULATION
// =============================================================================

/**
 * Type guard to check if a profile has Big Five modulation applied.
 */
export function isModulatedProfile(
  profile: BehaviorProfile | ModulatedBehaviorProfile
): profile is ModulatedBehaviorProfile {
  return "modulationApplied" in profile && profile.modulationApplied === true
}

/**
 * Get extensions from profile, returning defaults if not modulated.
 */
export function getExtensions(
  profile: BehaviorProfile | ModulatedBehaviorProfile,
  fallbackBase?: BehaviorProfile
): ModulatedBehaviorExtensions {
  if (isModulatedProfile(profile)) {
    return profile.extensions
  }
  return createDefaultExtensions(fallbackBase ?? profile)
}

// =============================================================================
// INTEGRATION HELPER
// =============================================================================

/**
 * Apply Big Five modulation if BigFiveProfile is provided.
 * Returns unmodified base profile if bigFive is undefined.
 */
export function maybeApplyBigFiveModulation(
  base: BehaviorProfile,
  bigFive: BigFiveProfile | undefined,
  relationship: RelationshipState,
  hoursInactive?: number
): ModulatedBehaviorProfile | BehaviorProfile {
  if (!bigFive) {
    return base
  }
  
  const result = applyBigFiveModulation({
    base,
    bigFive,
    relationship,
    hoursInactive,
  })
  
  return result.profile
}

// =============================================================================
// TESTING: INLINE ASSERTIONS
// =============================================================================

/**
 * Run basic sanity checks on modulation logic.
 * Call this in development to verify rules work as expected.
 */
export function runModulationTests(): void {
  const baseTraits = {
    emotionalStyle: "Caring" as const,
    attachmentStyle: "Emotionally present" as const,
    reactionToAbsence: "Medium" as const,
    communicationStyle: "Soft" as const,
    relationshipPace: "Natural" as const,
    culturalPersonality: "Warm Slavic" as const,
  }
  
  // Mock base profile (simplified)
  const mockBase: BehaviorProfile = {
    tone: {
      warmth: 0.7,
      playfulness: 0.5,
      expressiveness: 0.6,
      vulnerability: 0.6,
      assertiveness: 0.4,
      formality: 0.3,
    },
    messageStyling: {
      response: {
        avgSentenceLength: "medium",
        preferredMessageLength: 25,
        usesFillerWords: true,
        usesContractions: true,
        punctuationStyle: "standard",
        capitalizationStyle: "standard",
      },
      emoji: {
        frequency: "moderate",
        preferredEmojis: ["😊", "❤️"],
        heartsFrequency: "moderate",
        usesKaomoji: false,
      },
      petNames: {
        enabled: true,
        startAtLevel: "FAMILIAR",
        casualNames: ["sweetie"],
        affectionateNames: ["honey"],
        intimateNames: ["love"],
      },
    },
    relationship: {
      trustGainBase: 1.2,
      trustGainBonusEmotional: 1.0,
      intimacyGainBase: 1.5,
      intimacyGainBonusAffection: 1.0,
      decayRatePerDay: 2.0,
      decayStartHours: 24,
      levelUpBonusMultiplier: 1.2,
    },
    initiation: {
      baseFrequency: 0.15,
      cooldownHours: 5,
      preferredTimeOfDay: "evening",
      messageVariety: "medium",
      levelMultipliers: {
        STRANGER: 0,
        FAMILIAR: 0.7,
        CLOSE: 1.0,
        INTIMATE: 1.3,
        EXCLUSIVE: 1.5,
      },
    },
    absence: {
      triggerHours: 30,
      escalationHours: 24,
      maxIntensity: "moderate",
      messageStyle: "teasing",
    },
    prompt: {
      tone: {
        warmth: 0.7,
        playfulness: 0.5,
        expressiveness: 0.6,
        vulnerability: 0.6,
        assertiveness: 0.4,
        formality: 0.3,
      },
      responsePatterns: [],
      avoidPatterns: [],
      contextualRules: [],
    },
    derivedFrom: baseTraits,
  }
  
  const mockRelationship: RelationshipState = {
    trust: 50,
    intimacy: 50,
    level: "CLOSE",
    last_interaction_at: new Date().toISOString(),
    milestones_reached: [],
  }
  
  // Test 1: High extraversion increases initiation
  const highE: BigFiveProfile = {
    values: { openness: 50, conscientiousness: 50, extraversion: 90, agreeableness: 50, neuroticism: 50 },
    source: "trait_mapped",
  }
  const result1 = applyBigFiveModulation({ base: mockBase, bigFive: highE, relationship: mockRelationship })
  console.assert(
    result1.profile.initiation.baseFrequency > mockBase.initiation.baseFrequency,
    "High E should increase initiation frequency"
  )
  console.assert(
    result1.profile.initiation.cooldownHours < mockBase.initiation.cooldownHours,
    "High E should decrease cooldown"
  )
  
  // Test 2: High neuroticism increases reassurance, softens style
  const highN: BigFiveProfile = {
    values: { openness: 50, conscientiousness: 50, extraversion: 50, agreeableness: 50, neuroticism: 95 },
    source: "trait_mapped",
  }
  const result2 = applyBigFiveModulation({ base: mockBase, bigFive: highN, relationship: mockRelationship })
  console.assert(
    result2.profile.extensions.affection.reassuranceLevel >= 2,
    "High N should increase reassurance"
  )
  console.assert(
    result2.profile.absence.messageStyle === "neutral",
    "High N should soften absence style"
  )
  
  // Test 3: High conscientiousness decreases emoji and intensity
  const highC: BigFiveProfile = {
    values: { openness: 50, conscientiousness: 95, extraversion: 50, agreeableness: 50, neuroticism: 50 },
    source: "trait_mapped",
  }
  const result3 = applyBigFiveModulation({ base: mockBase, bigFive: highC, relationship: mockRelationship })
  console.assert(
    result3.profile.extensions.phrasing.emojiRate <= 2,
    "High C should limit emoji rate"
  )
  
  // Test 4: Stranger level enforces conservative settings
  const strangerRelationship: RelationshipState = {
    trust: 10,
    intimacy: 10,
    level: "STRANGER",
    last_interaction_at: new Date().toISOString(),
    milestones_reached: [],
  }
  const result4 = applyBigFiveModulation({ base: mockBase, bigFive: highE, relationship: strangerRelationship })
  console.assert(
    result4.profile.initiation.cooldownHours >= 8,
    "Stranger should have cooldown >= 8"
  )
  console.assert(
    result4.profile.messageStyling.petNames.enabled === false,
    "Stranger should have pet names disabled"
  )
  
  console.log("✓ All Big Five modulation tests passed")
}
