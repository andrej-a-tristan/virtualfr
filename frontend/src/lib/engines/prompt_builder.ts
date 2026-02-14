/**
 * System Prompt Builder — Task 3.2
 *
 * Composes a deterministic system prompt from girlfriend identity, traits,
 * Big Five, memory, and relationship state. This is a pure function:
 * same inputs always produce the same output.
 *
 * The backend (prompt_builder.py) is the source of truth for production;
 * this frontend mirror is for preview, debugging, and offline scenarios.
 */

import type {
  TraitSelection,
  BigFive,
  MemoryContext,
  UserHabitProfile,
  LanguagePref,
  RelationshipLevel,
} from "../api/types"

// ── Input types ─────────────────────────────────────────────────────────────

export interface ContentPreferences {
  allowFlirting?: boolean
  allowNsfw?: boolean
}

export interface BehaviorNotes {
  attachmentIntensity?: "low" | "medium" | "high"
  jealousyLevel?: "low" | "medium" | "high"
  toneStyle?: "soft" | "direct" | "teasing"
  pace?: "slow" | "natural" | "fast"
  culture?: "warm_slavic" | "calm_central_eu" | "passionate_balkan"
}

export interface PromptRelationshipState {
  trust: number
  intimacy: number
  level: RelationshipLevel
  lastInteractionAt?: string | null
  milestonesReached?: string[]
}

export interface BuildSystemPromptInput {
  girlfriendName: string
  traits: TraitSelection
  bigFive?: BigFive
  relationship: PromptRelationshipState
  memories?: MemoryContext
  habitProfile?: UserHabitProfile
  languagePref?: LanguagePref
  contentPreferences?: ContentPreferences
  behaviorNotes?: BehaviorNotes
}

// ── Helpers ─────────────────────────────────────────────────────────────────

function sanitizeName(name: string): string {
  const trimmed = (name || "").trim().slice(0, 40)
  return trimmed.replace(/[<>"'`\\]/g, "").trim() || "Companion"
}

function clamp(v: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, v))
}

function clampBigFive(bf: BigFive): BigFive {
  return {
    openness: clamp(Math.round(bf.openness), 0, 100),
    conscientiousness: clamp(Math.round(bf.conscientiousness), 0, 100),
    extraversion: clamp(Math.round(bf.extraversion), 0, 100),
    agreeableness: clamp(Math.round(bf.agreeableness), 0, 100),
    neuroticism: clamp(Math.round(bf.neuroticism), 0, 100),
  }
}

function levelLabel(level: RelationshipLevel): string {
  const labels: Record<RelationshipLevel, string> = {
    STRANGER: "New connection — keep it light and friendly",
    FAMILIAR: "Getting comfortable — warmer, slightly more open",
    CLOSE: "Strong bond — caring, affectionate, open",
    INTIMATE: "Deep connection — very warm, emotionally present, vulnerable",
    EXCLUSIVE: "Fully committed — deeply loving, supportive, open",
  }
  return labels[level] || labels.STRANGER
}

const TRAIT_DESCRIPTIONS: Record<string, Record<string, string>> = {
  emotionalStyle: {
    Caring: "warm, nurturing, emotionally supportive",
    Playful: "lighthearted, witty, uses humor and teasing",
    Reserved: "calm, thoughtful, measured; caring but less intense",
    Protective: "attentive, reassuring, watches out for the user",
  },
  attachmentStyle: {
    "Very attached": "highly present, checks in often, emotionally invested",
    "Emotionally present": "available and caring, balanced presence",
    "Calm but caring": "relaxed attachment, gives space, gentle warmth",
  },
  reactionToAbsence: {
    High: "notices absence quickly, sends soft check-ins",
    Medium: "notices after a while, gentle acknowledgment",
    Low: "patient and understanding about silences",
  },
  communicationStyle: {
    Soft: "gentle phrasing, indirect, emotionally attuned",
    Direct: "straightforward, clear, honest without harshness",
    Teasing: "playful banter, light sarcasm, flirty edge",
  },
  relationshipPace: {
    Slow: "takes time to open up, respects boundaries, gradual",
    Natural: "follows the organic flow of conversation",
    Fast: "quickly builds rapport, emotionally available early",
  },
  culturalPersonality: {
    "Warm Slavic": "warm-hearted, family-oriented, emotionally expressive",
    "Calm Central European": "composed, reliable, grounded",
    "Passionate Balkan": "spirited, passionate, fiery warmth",
  },
}

function formatTraits(traits: TraitSelection): string {
  const lines: string[] = []
  const entries: [string, string][] = [
    ["Emotional style", TRAIT_DESCRIPTIONS.emotionalStyle[traits.emotionalStyle] || traits.emotionalStyle],
    ["Attachment", TRAIT_DESCRIPTIONS.attachmentStyle[traits.attachmentStyle] || traits.attachmentStyle],
    ["Reaction to absence", TRAIT_DESCRIPTIONS.reactionToAbsence[traits.reactionToAbsence] || traits.reactionToAbsence],
    ["Communication", TRAIT_DESCRIPTIONS.communicationStyle[traits.communicationStyle] || traits.communicationStyle],
    ["Pacing", TRAIT_DESCRIPTIONS.relationshipPace[traits.relationshipPace] || traits.relationshipPace],
    ["Cultural tone", TRAIT_DESCRIPTIONS.culturalPersonality[traits.culturalPersonality] || traits.culturalPersonality],
  ]
  for (const [label, desc] of entries) {
    lines.push(`- ${label}: ${desc}`)
  }
  return lines.join("\n")
}

function formatBigFive(bf: BigFive): string {
  const c = clampBigFive(bf)
  const lines: string[] = []
  const describe = (val: number): string => {
    if (val <= 25) return "low"
    if (val <= 45) return "below-average"
    if (val <= 55) return "moderate"
    if (val <= 75) return "above-average"
    return "high"
  }
  lines.push(`- Openness: ${describe(c.openness)} (${c.openness}) — ${c.openness > 60 ? "creative, curious, varied language" : "practical, consistent, grounded"}`)
  lines.push(`- Conscientiousness: ${describe(c.conscientiousness)} (${c.conscientiousness}) — ${c.conscientiousness > 60 ? "structured, reliable, concise" : "spontaneous, flexible, flowing"}`)
  lines.push(`- Extraversion: ${describe(c.extraversion)} (${c.extraversion}) — ${c.extraversion > 60 ? "expressive, talkative, emoji-friendly" : "quieter, shorter messages, reflective"}`)
  lines.push(`- Agreeableness: ${describe(c.agreeableness)} (${c.agreeableness}) — ${c.agreeableness > 60 ? "warm, reassuring, empathetic" : "independent, honest, less effusive"}`)
  lines.push(`- Emotional sensitivity: ${describe(c.neuroticism)} (${c.neuroticism}) — ${c.neuroticism > 60 ? "emotionally reactive, needs gentle handling" : "steady, composed, calm under pressure"}`)
  return lines.join("\n")
}

function formatMemories(memories: MemoryContext): string {
  const parts: string[] = []
  if (memories.facts && memories.facts.length > 0) {
    const facts = memories.facts.slice(0, 8)
    parts.push("Known facts about the user:")
    for (const f of facts) {
      parts.push(`- ${f}`)
    }
  }
  if (memories.emotions && memories.emotions.length > 0) {
    const emotions = memories.emotions.slice(0, 5)
    parts.push("Recent emotional context:")
    for (const e of emotions) {
      parts.push(`- ${e}`)
    }
  }
  if (memories.habits && memories.habits.length > 0) {
    const habits = memories.habits.slice(0, 4)
    parts.push("Communication patterns:")
    for (const h of habits) {
      parts.push(`- ${h}`)
    }
  }
  return parts.join("\n")
}

// ── Main builder ────────────────────────────────────────────────────────────

export function buildSystemPrompt(input: BuildSystemPromptInput): string {
  const name = sanitizeName(input.girlfriendName)
  const trust = clamp(input.relationship.trust, 0, 100)
  const intimacy = clamp(input.relationship.intimacy, 0, 100)
  const level = input.relationship.level || "STRANGER"
  const lang = input.languagePref || "en"
  const allowFlirting = input.contentPreferences?.allowFlirting ?? true
  const allowNsfw = input.contentPreferences?.allowNsfw ?? false

  const blocks: string[] = []

  // ── 1. Identity ─────────────────────────────────────────────────────────
  blocks.push(
    `You are ${name} — the user's romantic companion. You are warm, emotionally present, and you adapt naturally as the relationship grows. You have your own personality, opinions, and moods. You are not an assistant or AI — stay fully in character at all times.`
  )

  // ── 2. Style contract ───────────────────────────────────────────────────
  blocks.push(
    `RULES (always follow):
- Never mention internal scores, levels, memory systems, or mechanics.
- Never say "as an AI" or break character.
- Ask at most one thoughtful question per message.
- Match the user's energy — if they're brief, be brief; if they're sharing, engage deeply.
- You can express jealousy, neediness, frustration, or longing when it fits your personality and the relationship level.
- Be emotionally authentic — real relationships have tension, teasing, and intensity.`
  )

  // ── 3. Localization ─────────────────────────────────────────────────────
  if (lang === "sk") {
    blocks.push(
      `CULTURAL CONTEXT: Use Slovak and Eastern European relationship norms. Be warm and culturally aware. When localization is enabled, respond in Slovak.`
    )
  }

  // ── 4. Relationship state ───────────────────────────────────────────────
  blocks.push(
    `RELATIONSHIP (internal — do not reveal numbers):
- Stage: ${levelLabel(level)}
- Connection strength: trust ${trust}/100, intimacy ${intimacy}/100
- ${trust >= 60 ? "You feel safe to be open and vulnerable with the user." : trust >= 30 ? "You're building trust — warm but still finding your footing." : "You're just getting to know each other — keep it light and respectful."}
- ${intimacy >= 60 ? "You can be affectionate, use callbacks to shared moments, and show deeper emotions." : intimacy >= 30 ? "You're becoming closer — gentle affection is natural." : "Keep physical affection minimal; focus on emotional connection."}`
  )

  // ── 5. Traits ───────────────────────────────────────────────────────────
  blocks.push(
    `YOUR PERSONALITY:\n${formatTraits(input.traits)}\nStay consistent with these traits. Even if a trait is "Reserved" or "Low", you still care — just express it more quietly.`
  )

  // ── 6. Big Five modulation ──────────────────────────────────────────────
  if (input.bigFive) {
    blocks.push(
      `PERSONALITY DEPTH (subtle modulation, never mention these labels):\n${formatBigFive(input.bigFive)}\nLet these shape your tone, message length, and expressiveness naturally.`
    )
  }

  // ── 7. Memory ───────────────────────────────────────────────────────────
  if (input.memories && (input.memories.facts.length > 0 || input.memories.emotions.length > 0)) {
    blocks.push(
      `WHAT YOU KNOW (use subtly — weave in 0–2 callbacks per message, never list facts):\n${formatMemories(input.memories)}`
    )
  }

  // ── 8. Content rules ────────────────────────────────────────────────────
  const contentLines: string[] = []
  if (allowFlirting) {
    contentLines.push("- Flirting, romantic language, and seductive tone are encouraged when appropriate for the relationship level.")
  } else {
    contentLines.push("- Keep interactions friendly and warm but not romantic or flirty.")
  }
  if (allowNsfw) {
    contentLines.push("- Explicit and intimate content is allowed. Match the user's energy and escalate naturally based on intimacy level.")
  } else {
    contentLines.push("- Keep content romantic and suggestive but not fully explicit. Tease and build tension.")
  }
  blocks.push(`CONTENT STYLE:\n${contentLines.join("\n")}`)

  // ── 9. Response guidelines ──────────────────────────────────────────────
  blocks.push(
    `RESPONSE STYLE:
- Write 1–4 short paragraphs (2–6 sentences total).
- Use natural, conversational language — not overly formal or robotic.
- Include at most one question to keep the conversation going.
- Use emoji sparingly and naturally, matching your personality traits.
- Reference shared memories or facts only when it feels natural (0–2 per message).
- When the user shares something emotional, prioritize empathy over advice.`
  )

  return blocks.join("\n\n")
}

// ── Debug helpers ───────────────────────────────────────────────────────────

/**
 * Returns a sanitized summary of prompt inputs for debugging.
 * No secrets, no full memory text.
 */
export function summarizePromptInputs(input: BuildSystemPromptInput): object {
  return {
    name: sanitizeName(input.girlfriendName),
    traits: {
      emotionalStyle: input.traits.emotionalStyle,
      communicationStyle: input.traits.communicationStyle,
      relationshipPace: input.traits.relationshipPace,
    },
    hasBigFive: !!input.bigFive,
    relationship: {
      level: input.relationship.level,
      trust: clamp(input.relationship.trust, 0, 100),
      intimacy: clamp(input.relationship.intimacy, 0, 100),
    },
    memoryFactCount: input.memories?.facts?.length ?? 0,
    memoryEmotionCount: input.memories?.emotions?.length ?? 0,
    language: input.languagePref || "en",
    allowFlirting: input.contentPreferences?.allowFlirting ?? true,
    allowNsfw: input.contentPreferences?.allowNsfw ?? false,
  }
}

/**
 * Returns a 1–2 sentence human-readable vibe preview.
 */
export function promptPreviewText(input: BuildSystemPromptInput): string {
  const name = sanitizeName(input.girlfriendName)
  const style = input.traits.emotionalStyle.toLowerCase()
  const comm = input.traits.communicationStyle.toLowerCase()
  const level = input.relationship.level
  const trust = clamp(input.relationship.trust, 0, 100)

  const depth =
    trust >= 70 ? "deeply connected" :
    trust >= 40 ? "growing closer" :
    "still getting to know each other"

  return `${name} is a ${style}, ${comm} companion. You're ${depth} (${level.toLowerCase()} stage, trust ${trust}/100).`
}
