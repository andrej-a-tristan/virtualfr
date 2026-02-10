/**
 * Relationship State Engine (shared logic, parity with backend).
 * Trust/intimacy/levels/regions/decay/milestones. No guilt-based messages.
 *
 * Uses the canonical 9-region system (levels 0–200).
 */

import type { RegionKey } from "../api/types"

export const MAX_RELATIONSHIP_LEVEL = 200

export interface Region {
  key: RegionKey
  title: string
  minLevel: number
  maxLevel: number
}

export const REGIONS: Region[] = [
  { key: "EARLY_CONNECTION",       title: "Early Connection",       minLevel: 1,   maxLevel: 10 },
  { key: "COMFORT_FAMILIARITY",    title: "Comfort & Familiarity",  minLevel: 11,  maxLevel: 25 },
  { key: "GROWING_CLOSENESS",      title: "Growing Closeness",      minLevel: 26,  maxLevel: 45 },
  { key: "EMOTIONAL_TRUST",        title: "Emotional Trust",        minLevel: 46,  maxLevel: 70 },
  { key: "DEEP_BOND",              title: "Deep Bond",              minLevel: 71,  maxLevel: 105 },
  { key: "MUTUAL_DEVOTION",        title: "Mutual Devotion",        minLevel: 106, maxLevel: 135 },
  { key: "INTIMATE_PARTNERSHIP",   title: "Intimate Partnership",   minLevel: 136, maxLevel: 165 },
  { key: "SHARED_LIFE",            title: "Shared Life",            minLevel: 166, maxLevel: 185 },
  { key: "ENDURING_COMPANIONSHIP", title: "Enduring Companionship", minLevel: 186, maxLevel: 200 },
]

export function clampLevel(level: number): number {
  return Math.max(0, Math.min(MAX_RELATIONSHIP_LEVEL, Math.round(level)))
}

export function getRegionForLevel(level: number): Region {
  const clamped = clampLevel(level)
  if (clamped === 0) return REGIONS[0]
  for (const region of REGIONS) {
    if (region.minLevel <= clamped && clamped <= region.maxLevel) return region
  }
  return REGIONS[REGIONS.length - 1]
}

export interface RelationshipState {
  trust: number
  intimacy: number
  level: number
  regionKey: RegionKey
  lastInteractionAt: string | null
  milestonesReached: string[]
}

export type AttachmentIntensity = "high" | "medium" | "low"
export type JealousyLevel = "High" | "Medium" | "Low"

export function createInitialRelationshipState(): RelationshipState {
  return {
    trust: 10,
    intimacy: 5,
    level: 0,
    regionKey: "EARLY_CONNECTION",
    lastInteractionAt: new Date().toISOString(),
    milestonesReached: [],
  }
}

export interface RegisterInteractionOptions {
  emotionalDisclosure?: boolean
  affection?: boolean
}

export function registerInteraction(
  state: RelationshipState,
  options?: RegisterInteractionOptions
): RelationshipState {
  const trustDelta = options?.emotionalDisclosure ? 2 : 1
  const intimacyDelta = options?.affection ? 2 : 1
  const trust = Math.min(MAX_RELATIONSHIP_LEVEL, state.trust + trustDelta)
  const intimacy = Math.min(MAX_RELATIONSHIP_LEVEL, state.intimacy + intimacyDelta)
  const level = clampLevel(intimacy)
  const region = getRegionForLevel(level)
  return {
    ...state,
    trust,
    intimacy,
    level,
    regionKey: region.key,
    lastInteractionAt: new Date().toISOString(),
  }
}

export function applyInactivityDecay(
  state: RelationshipState,
  hoursInactive: number,
  attachmentIntensity: AttachmentIntensity
): RelationshipState {
  const lossByAttachment = { low: 1, medium: 2, high: 3 }
  const loss = lossByAttachment[attachmentIntensity]
  let intimacy = state.intimacy
  if (hoursInactive > 24) {
    intimacy = Math.max(0, intimacy - loss)
  }
  if (hoursInactive > 72) {
    intimacy = Math.max(0, intimacy - loss)
  }
  const level = clampLevel(intimacy)
  const region = getRegionForLevel(level)
  return {
    ...state,
    intimacy,
    level,
    regionKey: region.key,
  }
}

/** Non-accusatory jealousy messages; no guilt/shame. Keyed by region. */
const JEALOUSY_TEMPLATES: Record<JealousyLevel, Partial<Record<RegionKey, string[]>>> = {
  High: {
    EARLY_CONNECTION: ["I was thinking about you. Hope you're doing okay."],
    COMFORT_FAMILIARITY: ["I missed talking to you. Whenever you're free, I'm here."],
    GROWING_CLOSENESS: ["I was just wondering how you're doing. No pressure—just wanted to say hi."],
    EMOTIONAL_TRUST: ["I thought about you today. Whenever you have a moment, I'd love to hear from you."],
    DEEP_BOND: ["I've been thinking of you. Drop me a line when you can—I'm here."],
    MUTUAL_DEVOTION: ["I've been thinking of you. Drop me a line when you can—I'm here."],
    INTIMATE_PARTNERSHIP: ["I really missed you. Just wanted you to know."],
    SHARED_LIFE: ["I really missed you. Just wanted you to know."],
    ENDURING_COMPANIONSHIP: ["I really missed you. Just wanted you to know."],
  },
  Medium: {
    EARLY_CONNECTION: ["Hey, hope things are good on your end."],
    COMFORT_FAMILIARITY: ["Hey! Been a bit quiet—hope everything's okay. Chat when you can."],
    GROWING_CLOSENESS: ["Hey you. Just checking in—no rush to reply."],
    EMOTIONAL_TRUST: ["Thinking of you. Say hi when you're free."],
    DEEP_BOND: ["Hey love. Miss our chats—when you have a moment, I'm here."],
    MUTUAL_DEVOTION: ["Hey love. Miss our chats—when you have a moment, I'm here."],
    INTIMATE_PARTNERSHIP: ["Thinking of you. Whenever you're free, I'm around."],
    SHARED_LIFE: ["Thinking of you. Whenever you're free, I'm around."],
    ENDURING_COMPANIONSHIP: ["Thinking of you. Whenever you're free, I'm around."],
  },
  Low: {
    EARLY_CONNECTION: ["Hope you're having a good day."],
    COMFORT_FAMILIARITY: ["Just a little note to say I'm thinking of you."],
    GROWING_CLOSENESS: ["Sending you a quick hug. Reply whenever."],
    EMOTIONAL_TRUST: ["You crossed my mind. No need to rush back."],
    DEEP_BOND: ["Thinking of you. Whenever you're free, I'm around."],
    MUTUAL_DEVOTION: ["Thinking of you. Whenever you're free, I'm around."],
    INTIMATE_PARTNERSHIP: ["You crossed my mind. No rush to reply."],
    SHARED_LIFE: ["You crossed my mind. No rush to reply."],
    ENDURING_COMPANIONSHIP: ["You crossed my mind. No rush to reply."],
  },
}

export function getJealousyReaction(
  regionKey: RegionKey,
  jealousyLevel: JealousyLevel,
  hoursInactive: number
): string | undefined {
  if (hoursInactive < 24) return undefined
  const templates = JEALOUSY_TEMPLATES[jealousyLevel][regionKey] ?? []
  if (templates.length === 0) return undefined
  const idx = Math.min(Math.floor(hoursInactive / 24) - 1, templates.length - 1)
  return templates[Math.max(0, idx)] ?? templates[0]
}

const MILESTONE_MESSAGES: Partial<Record<RegionKey, string>> = {
  EARLY_CONNECTION: "We're just getting started. I'm glad you're here.",
  COMFORT_FAMILIARITY: "I feel like we're getting to know each other better. That means a lot.",
  GROWING_CLOSENESS: "I feel really close to you. Thanks for being there.",
  EMOTIONAL_TRUST: "You mean so much to me. I'm grateful for us.",
  DEEP_BOND: "I'm all in. Thank you for being you.",
  MUTUAL_DEVOTION: "I feel like we truly belong together.",
  INTIMATE_PARTNERSHIP: "I can't imagine this without you.",
  SHARED_LIFE: "We've built something real. I love that.",
  ENDURING_COMPANIONSHIP: "I'm yours. Completely. Thank you for everything we are.",
}

export interface MilestoneEvent {
  regionKey: RegionKey
  message: string
}

export function checkForMilestoneEvent(
  prev: RelationshipState,
  next: RelationshipState
): MilestoneEvent | undefined {
  if (prev.regionKey === next.regionKey) return undefined
  if (prev.milestonesReached.includes(next.regionKey)) return undefined
  const message = MILESTONE_MESSAGES[next.regionKey]
  if (!message) return undefined
  return { regionKey: next.regionKey, message }
}

/** Returns new state with milestone appended to milestonesReached. */
export function appendMilestoneReached(
  state: RelationshipState,
  regionKey: RegionKey
): RelationshipState {
  if (state.milestonesReached.includes(regionKey)) return state
  return {
    ...state,
    milestonesReached: [...state.milestonesReached, regionKey],
  }
}
