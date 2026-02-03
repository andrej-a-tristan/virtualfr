/**
 * Deterministic vibe summary and "How she'll treat you" bullets from trait selection.
 * No LLM — computed from choices for consistent, retention-safe copy.
 */
import type { TraitSelection } from "@/lib/api/types"

export function getVibeSummary(traits: Partial<TraitSelection>): string {
  if (!traits.emotionalStyle && !traits.attachmentStyle) {
    return "Your companion will reflect the choices you make below. Every option shows care—only the style changes."
  }
  const parts: string[] = []
  if (traits.emotionalStyle) {
    const e = traits.emotionalStyle
    if (e === "Caring") parts.push("She’s warm and nurturing")
    else if (e === "Playful") parts.push("She’s light-hearted and fun")
    else if (e === "Reserved") parts.push("She’s a calm, steady presence")
    else if (e === "Protective") parts.push("She’s strong and has your back")
  }
  if (traits.culturalPersonality) {
    const c = traits.culturalPersonality
    if (c === "Warm Slavic") parts.push("with a loyal, big-hearted spirit")
    else if (c === "Calm Central European") parts.push("with an elegant, grounded vibe")
    else if (c === "Passionate Balkan") parts.push("with fire and expressiveness")
  }
  if (parts.length === 0) return "She’ll match the energy you choose—all options still care."
  return parts.join(", ") + "."
}

export function getHowSheTreatsYou(traits: Partial<TraitSelection>): string[] {
  const bullets: string[] = []
  if (traits.attachmentStyle) {
    const a = traits.attachmentStyle
    if (a === "Very attached")
      bullets.push("She’ll want to be a big part of your day and will let you know when she misses you.")
    else if (a === "Emotionally present")
      bullets.push("She’ll stay close with regular check-ins and thoughtful messages.")
    else if (a === "Calm but caring")
      bullets.push("She’ll be there whenever you need her, with a secure, easy-going bond.")
  }
  if (traits.communicationStyle) {
    const c = traits.communicationStyle
    if (c === "Soft")
      bullets.push("Her tone will be gentle and sweet, with plenty of warmth and care.")
    else if (c === "Direct")
      bullets.push("She’ll be bold and honest—she says exactly what she thinks.")
    else if (c === "Teasing")
      bullets.push("She’ll keep you on your toes with witty banter and playful back-and-forth.")
  }
  if (traits.emotionalStyle) {
    const e = traits.emotionalStyle
    if (e === "Caring")
      bullets.push("When you’re stressed, she’ll comfort you and remind you things will be okay.")
    else if (e === "Playful")
      bullets.push("When you’re down, she’ll lift your spirits with humor and wit.")
    else if (e === "Reserved")
      bullets.push("When you need support, she’ll be a calm presence without overwhelming you.")
    else if (e === "Protective")
      bullets.push("When life gets heavy, she’ll take charge so you feel like you’ve got backup.")
  }
  if (traits.reactionToAbsence) {
    const r = traits.reactionToAbsence
    if (r === "High")
      bullets.push("If you’re busy, she’ll tell you she misses you and that she’s waiting for you.")
    else if (r === "Medium")
      bullets.push("If you disappear for a bit, she’ll tease you about it in a fun way.")
    else if (r === "Low")
      bullets.push("If you’re away, she’ll send a sweet note when she can—no pressure.")
  }
  if (traits.relationshipPace) {
    const p = traits.relationshipPace
    if (p === "Slow")
      bullets.push("She’ll want to build a deep connection before opening up fully.")
    else if (p === "Natural")
      bullets.push("She’ll let things flow naturally and see where the spark takes you.")
    else if (p === "Fast")
      bullets.push("She’s ready to feel the chemistry right away and won’t hold back.")
  }
  if (traits.culturalPersonality) {
    const c = traits.culturalPersonality
    if (c === "Warm Slavic")
      bullets.push("Her personality is deeply loyal and nurturing—a heart of gold.")
    else if (c === "Calm Central European")
      bullets.push("She brings an elegant, sophisticated vibe to everything.")
    else if (c === "Passionate Balkan")
      bullets.push("She’s spirited, intense, and expressive in the best way.")
  }
  return bullets
}
