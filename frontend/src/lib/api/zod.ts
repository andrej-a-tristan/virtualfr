/** Zod schemas for form validation / API parsing */
import { z } from "zod"

export const signupSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
  display_name: z.string().optional(),
})

export const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
})

/** Trait selection schema: all fields required, displayName 1–24 chars. */
export const traitSelectionSchema = z.object({
  displayName: z.string().min(1, "Name is required").max(24, "Max 24 characters"),
  traits: z.object({
    emotionalStyle: z.enum(["Caring", "Playful", "Reserved", "Protective"]),
    attachmentStyle: z.enum(["Very attached", "Emotionally present", "Calm but caring"]),
    reactionToAbsence: z.enum(["High", "Medium", "Low"]),
    communicationStyle: z.enum(["Soft", "Direct", "Teasing"]),
    relationshipPace: z.enum(["Slow", "Natural", "Fast"]),
    culturalPersonality: z.enum(["Warm Slavic", "Calm Central European", "Passionate Balkan"]),
  }),
})

export type SignupInput = z.infer<typeof signupSchema>
export type LoginInput = z.infer<typeof loginSchema>
export type TraitSelectionInput = z.infer<typeof traitSelectionSchema>
