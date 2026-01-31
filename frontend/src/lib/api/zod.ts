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

export type SignupInput = z.infer<typeof signupSchema>
export type LoginInput = z.infer<typeof loginSchema>
export type TraitsInput = z.infer<typeof traitsSchema>
