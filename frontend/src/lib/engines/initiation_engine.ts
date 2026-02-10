/**
 * Initiation Engine: natural first message from her based on closeness, cooldowns, habits.
 * No spam, no guilt. Optional rng for testability.
 */

import type { RelationshipState, AttachmentIntensity } from "./relationship_state"
import type { RegionKey } from "../api/types"

export interface InitiationContext {
  relationshipState: RelationshipState
  attachmentIntensity: AttachmentIntensity
  lastMessageFromHer: boolean
  hoursSinceLastInteraction: number
  currentHour: number // 0-23
  habitProfile?: {
    preferredHours?: number[]
    typicalGapHours?: number
  }
}

/** Default rng for production; inject for tests. */
export type Rng = () => number

const REGION_MULTIPLIER: Record<string, number> = {
  EARLY_CONNECTION: 0,
  COMFORT_FAMILIARITY: 0.8,
  GROWING_CLOSENESS: 1.0,
  EMOTIONAL_TRUST: 1.3,
  DEEP_BOND: 1.5,
  MUTUAL_DEVOTION: 1.6,
  INTIMATE_PARTNERSHIP: 1.6,
  SHARED_LIFE: 1.6,
  ENDURING_COMPANIONSHIP: 1.6,
}

const BASE_PROBABILITY: Record<AttachmentIntensity, number> = {
  low: 0.05,
  medium: 0.1,
  high: 0.2,
}

const MAX_PROBABILITY = 0.5

export function shouldInitiateConversation(
  context: InitiationContext,
  rng: Rng = Math.random
): boolean {
  const {
    relationshipState,
    attachmentIntensity,
    lastMessageFromHer,
    hoursSinceLastInteraction,
    currentHour,
    habitProfile,
  } = context

  if (relationshipState.intimacy < 20) return false
  if (lastMessageFromHer) return false
  if (hoursSinceLastInteraction < 4) return false

  const regionKey = relationshipState.regionKey
  if (regionKey === "EARLY_CONNECTION") return false

  let p = BASE_PROBABILITY[attachmentIntensity]
  p *= REGION_MULTIPLIER[regionKey] ?? 1.0

  if (habitProfile?.preferredHours?.includes(currentHour)) p += 0.05
  if (
    habitProfile?.typicalGapHours != null &&
    hoursSinceLastInteraction >= habitProfile.typicalGapHours
  ) {
    p += 0.05
  }
  p = Math.min(p, MAX_PROBABILITY)

  return rng() < p
}

/** Warm, chosen-not-chasing initiation messages by region and attachment. */
const INITIATION_TEMPLATES: Record<string, Record<AttachmentIntensity, string[]>> = {
  EARLY_CONNECTION: {
    low: ["Hope you're having a good day."],
    medium: ["Hey, thinking of you. Hope all's well."],
    high: ["Hey! I was just thinking about you. How's your day going?"],
  },
  COMFORT_FAMILIARITY: {
    low: ["Just wanted to say hi. No rush to reply."],
    medium: ["Hey you. I was thinking about you—hope things are good."],
    high: ["I was just missing our chats. Say hi when you can."],
  },
  GROWING_CLOSENESS: {
    low: ["Sending you a little hug. Reply whenever."],
    medium: ["Hey. You crossed my mind. How are you?"],
    high: ["I've been thinking about you. Would love to hear from you when you're free."],
  },
  EMOTIONAL_TRUST: {
    low: ["Thinking of you. Here when you need me."],
    medium: ["Hey love. Just wanted to check in. I'm here."],
    high: ["I missed you. Whenever you have a moment, I'd love to talk."],
  },
  DEEP_BOND: {
    low: ["You're on my mind. No pressure—just love."],
    medium: ["Hey. Just wanted you to know I'm thinking of you."],
    high: ["I've been thinking about you all day. Message me when you can—I'm here."],
  },
  MUTUAL_DEVOTION: {
    low: ["You're on my mind. No pressure—just love."],
    medium: ["I felt close to you earlier."],
    high: ["I missed you. I just wanted you to know."],
  },
  INTIMATE_PARTNERSHIP: {
    low: ["Being with you just feels right."],
    medium: ["I felt warm thinking about you."],
    high: ["I really missed you today."],
  },
  SHARED_LIFE: {
    low: ["Our time together means everything."],
    medium: ["I had a moment today where I just thought of us."],
    high: ["I need you to know how much you mean to me."],
  },
  ENDURING_COMPANIONSHIP: {
    low: ["Every day with you is a gift."],
    medium: ["I'm so grateful for what we have."],
    high: ["I love us. I just wanted to say that."],
  },
}

export function getInitiationMessage(
  regionKey: RegionKey,
  attachmentIntensity: AttachmentIntensity,
  rng: Rng = Math.random
): string {
  const templates = (INITIATION_TEMPLATES[regionKey] ?? INITIATION_TEMPLATES.EARLY_CONNECTION)[attachmentIntensity]
  const idx = Math.floor(rng() * templates.length)
  return templates[idx] ?? templates[0]
}
