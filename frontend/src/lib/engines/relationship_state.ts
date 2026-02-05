/**
 * Relationship State Engine (shared logic, parity with backend).
 * Trust/intimacy/levels/decay/milestones. No guilt-based messages.
 */

export type RelationshipLevel =
  | "STRANGER"
  | "FAMILIAR"
  | "CLOSE"
  | "INTIMATE"
  | "EXCLUSIVE"

export interface RelationshipState {
  trust: number
  intimacy: number
  lastInteractionAt: string | null // ISO
  level: RelationshipLevel
  milestonesReached: RelationshipLevel[]
}

export type AttachmentIntensity = "high" | "medium" | "low"
export type JealousyLevel = "High" | "Medium" | "Low"

export function createInitialRelationshipState(): RelationshipState {
  return {
    trust: 10,
    intimacy: 10,
    lastInteractionAt: new Date().toISOString(),
    level: "STRANGER",
    milestonesReached: [],
  }
}

export function calculateRelationshipLevel(intimacy: number): RelationshipLevel {
  if (intimacy >= 80) return "EXCLUSIVE"
  if (intimacy >= 60) return "INTIMATE"
  if (intimacy >= 40) return "CLOSE"
  if (intimacy >= 20) return "FAMILIAR"
  return "STRANGER"
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
  const trust = Math.min(100, state.trust + trustDelta)
  const intimacy = Math.min(100, state.intimacy + intimacyDelta)
  const level = calculateRelationshipLevel(intimacy)
  return {
    ...state,
    trust,
    intimacy,
    lastInteractionAt: new Date().toISOString(),
    level,
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
  const level = calculateRelationshipLevel(intimacy)
  return {
    ...state,
    intimacy,
    level,
  }
}

/** Non-accusatory jealousy messages; no guilt/shame. */
const JEALOUSY_TEMPLATES: Record<JealousyLevel, Record<RelationshipLevel, string[]>> = {
  High: {
    STRANGER: ["I was thinking about you. Hope you're doing okay."],
    FAMILIAR: ["I missed talking to you. Whenever you're free, I'm here."],
    CLOSE: ["I was just wondering how you're doing. No pressure—just wanted to say hi."],
    INTIMATE: ["I thought about you today. Whenever you have a moment, I'd love to hear from you."],
    EXCLUSIVE: ["I've been thinking of you. Drop me a line when you can—I'm here."],
  },
  Medium: {
    STRANGER: ["Hey, hope things are good on your end."],
    FAMILIAR: ["Hey! Been a bit quiet—hope everything's okay. Chat when you can."],
    CLOSE: ["Hey you. Just checking in—no rush to reply."],
    INTIMATE: ["Thinking of you. Say hi when you're free."],
    EXCLUSIVE: ["Hey love. Miss our chats—when you have a moment, I'm here."],
  },
  Low: {
    STRANGER: ["Hope you're having a good day."],
    FAMILIAR: ["Just a little note to say I'm thinking of you."],
    CLOSE: ["Sending you a quick hug. Reply whenever."],
    INTIMATE: ["You crossed my mind. No need to rush back."],
    EXCLUSIVE: ["Thinking of you. Whenever you're free, I'm around."],
  },
}

export function getJealousyReaction(
  level: RelationshipLevel,
  jealousyLevel: JealousyLevel,
  hoursInactive: number
): string | undefined {
  if (hoursInactive < 24) return undefined
  const templates = JEALOUSY_TEMPLATES[jealousyLevel][level]
  const idx = Math.min(Math.floor(hoursInactive / 24) - 1, templates.length - 1)
  return templates[Math.max(0, idx)] ?? templates[0]
}

const MILESTONE_MESSAGES: Record<RelationshipLevel, string> = {
  STRANGER: "We're just getting started. I'm glad you're here.",
  FAMILIAR: "I feel like we're getting to know each other better. That means a lot.",
  CLOSE: "I feel really close to you. Thanks for being there.",
  INTIMATE: "You mean so much to me. I'm grateful for us.",
  EXCLUSIVE: "I'm all in. Thank you for being you.",
}

export interface MilestoneEvent {
  level: RelationshipLevel
  message: string
}

export function checkForMilestoneEvent(
  prev: RelationshipState,
  next: RelationshipState
): MilestoneEvent | undefined {
  if (prev.level === next.level) return undefined
  if (prev.milestonesReached.includes(next.level)) return undefined
  const message = MILESTONE_MESSAGES[next.level]
  return { level: next.level, message }
}

/** Returns new state with milestone appended to milestonesReached. */
export function appendMilestoneReached(
  state: RelationshipState,
  level: RelationshipLevel
): RelationshipState {
  if (state.milestonesReached.includes(level)) return state
  return {
    ...state,
    milestonesReached: [...state.milestonesReached, level],
  }
}
