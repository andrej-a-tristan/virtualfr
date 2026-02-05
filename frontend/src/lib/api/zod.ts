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

/** Traits schema (snake_case for API). */
export const traitsSchema = z.object({
  emotional_style: z.enum(["Caring", "Playful", "Reserved", "Protective"]),
  attachment_style: z.enum(["Very attached", "Emotionally present", "Calm but caring"]),
  reaction_to_absence: z.enum(["High", "Medium", "Low"]),
  communication_style: z.enum(["Soft", "Direct", "Teasing"]),
  relationship_pace: z.enum(["Slow", "Natural", "Fast"]),
  cultural_personality: z.enum(["Warm Slavic", "Calm Central European", "Passionate Balkan"]),
})

export const appearanceSchema = z.object({
  vibe: z
    .enum(["cute", "elegant", "sporty", "goth", "girl-next-door", "model"])
    .optional(),
  age_range: z.enum(["18", "19-21", "22-26", "27+"]).optional(),
  ethnicity: z
    .enum(["any", "asian", "black", "latina", "white", "middle-eastern", "south-asian"])
    .optional(),
  breast_size: z.enum(["small", "medium", "large", "massive"]).optional(),
  butt_size: z.enum(["small", "medium", "large", "massive"]).optional(),
  hair_color: z
    .enum(["black", "brown", "blonde", "red", "ginger", "unnatural"])
    .optional(),
  hair_style: z.enum(["long", "bob", "curly", "straight", "bun"]).optional(),
  eye_color: z.enum(["brown", "blue", "green", "hazel"]).optional(),
  body_type: z.enum(["slim", "athletic", "curvy"]).optional(),
})

export const contentPrefsSchema = z.object({
  wants_spicy_photos: z.boolean(),
})

export type SignupInput = z.infer<typeof signupSchema>
export type LoginInput = z.infer<typeof loginSchema>
export type TraitSelectionInput = z.infer<typeof traitSelectionSchema>
export type TraitsInput = z.infer<typeof traitsSchema>
export type AppearanceInput = z.infer<typeof appearanceSchema>
export type ContentPrefsInput = z.infer<typeof contentPrefsSchema>
