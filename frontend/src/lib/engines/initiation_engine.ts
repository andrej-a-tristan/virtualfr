/**
 * Initiation Engine: natural first message from her based on closeness, cooldowns, habits.
 * No spam, no guilt. Optional rng for testability.
 */

import type { RelationshipState, RelationshipLevel } from "./relationship_state"
import type { AttachmentIntensity } from "./relationship_state"

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

const LEVEL_MULTIPLIER: Record<RelationshipLevel, number> = {
  STRANGER: 0,
  FAMILIAR: 0.8,
  CLOSE: 1.0,
  INTIMATE: 1.3,
  EXCLUSIVE: 1.6,
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

  let p = BASE_PROBABILITY[attachmentIntensity]
  p *= LEVEL_MULTIPLIER[relationshipState.level]
  if (relationshipState.level === "STRANGER") return false

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

/** Warm, chosen-not-chasing initiation messages by level and attachment. */
const INITIATION_TEMPLATES: Record<RelationshipLevel, Record<AttachmentIntensity, string[]>> = {
  STRANGER: {
    low: ["Hope you're having a good day."],
    medium: ["Hey, thinking of you. Hope all's well."],
    high: ["Hey! I was just thinking about you. How's your day going?"],
  },
  FAMILIAR: {
    low: ["Just wanted to say hi. No rush to reply."],
    medium: ["Hey you. I was thinking about you—hope things are good."],
    high: ["I was just missing our chats. Say hi when you can."],
  },
  CLOSE: {
    low: ["Sending you a little hug. Reply whenever."],
    medium: ["Hey. You crossed my mind. How are you?"],
    high: ["I've been thinking about you. Would love to hear from you when you're free."],
  },
  INTIMATE: {
    low: ["Thinking of you. Here when you need me."],
    medium: ["Hey love. Just wanted to check in. I'm here."],
    high: ["I missed you. Whenever you have a moment, I'd love to talk."],
  },
  EXCLUSIVE: {
    low: ["You're on my mind. No pressure—just love."],
    medium: ["Hey. Just wanted you to know I'm thinking of you."],
    high: ["I've been thinking about you all day. Message me when you can—I'm here."],
  },
}

export function getInitiationMessage(
  level: RelationshipLevel,
  attachmentIntensity: AttachmentIntensity,
  rng: Rng = Math.random
): string {
  const templates = INITIATION_TEMPLATES[level][attachmentIntensity]
  const idx = Math.floor(rng() * templates.length)
  return templates[idx] ?? templates[0]
}
