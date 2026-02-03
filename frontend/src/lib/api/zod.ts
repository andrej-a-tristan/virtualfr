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

export const traitsSchema = z.object({
  emotional_style: z.string().min(1),
  attachment_style: z.string().min(1),
  jealousy_level: z.string().min(1),
  communication_tone: z.string().min(1),
  intimacy_pace: z.string().min(1),
  cultural_personality: z.string().min(1),
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
export type TraitsInput = z.infer<typeof traitsSchema>
export type AppearanceInput = z.infer<typeof appearanceSchema>
export type ContentPrefsInput = z.infer<typeof contentPrefsSchema>
