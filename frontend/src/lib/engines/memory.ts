/**
 * Memory System (Task 1.2)
 * Frontend utilities for rendering memory context as UI components.
 * Types mirror backend services/memory.py.
 */

import type {
  MemoryContext,
  MemorySummary,
  FactualMemoryItem,
  EmotionalMemoryItem,
  MemoryType,
} from "../api/types"

// Re-export types for convenience
export type {
  MemoryContext,
  MemorySummary,
  FactualMemoryItem,
  EmotionalMemoryItem,
  MemoryType,
}

// -----------------------------------------------------------------------------
// Constants
// -----------------------------------------------------------------------------

/** Emotion tag colors for UI display */
export const EMOTION_COLORS: Record<string, string> = {
  stress: "bg-orange-100 text-orange-800",
  sadness: "bg-blue-100 text-blue-800",
  anger: "bg-red-100 text-red-800",
  fear: "bg-purple-100 text-purple-800",
  affection: "bg-pink-100 text-pink-800",
  excitement: "bg-yellow-100 text-yellow-800",
  happiness: "bg-green-100 text-green-800",
}

/** Valence emoji mapping */
export const VALENCE_EMOJI: Record<number, string> = {
  [-5]: "😢",
  [-4]: "😟",
  [-3]: "😞",
  [-2]: "😕",
  [-1]: "🙁",
  [0]: "😐",
  [1]: "🙂",
  [2]: "😊",
  [3]: "😄",
  [4]: "😍",
  [5]: "🥰",
}

/** Key to human-readable label mapping */
export const KEY_LABELS: Record<string, string> = {
  "user.name": "Name",
  "user.city": "City",
  "user.country": "Country",
  "user.study": "Studies",
  "user.work": "Job",
  "user.age": "Age",
  "pref.music": "Music",
  "pref.food": "Food",
  "pref.hobby": "Hobby",
  "pref.like": "Likes",
  "pref.dislike": "Dislikes",
  "schedule.exam": "Exam",
  "schedule.birthday": "Birthday",
}

// -----------------------------------------------------------------------------
// Render Helpers
// -----------------------------------------------------------------------------

/**
 * Get human-readable label for a fact key.
 * Handles dynamic keys like "pref.like.music" -> "Likes"
 */
export function getFactKeyLabel(key: string): string {
  if (KEY_LABELS[key]) return KEY_LABELS[key]
  if (key.startsWith("pref.like.")) return "Likes"
  if (key.startsWith("pref.dislike.")) return "Dislikes"
  // Fallback: convert key to title case
  return key.split(".").pop()?.replace(/_/g, " ") ?? key
}

/**
 * Get tailwind classes for an emotion tag.
 */
export function getEmotionTagClasses(tag: string): string {
  return EMOTION_COLORS[tag.toLowerCase()] ?? "bg-gray-100 text-gray-800"
}

/**
 * Get emoji for valence value.
 */
export function getValenceEmoji(valence: number): string {
  // Clamp to valid range
  const clamped = Math.max(-5, Math.min(5, valence))
  return VALENCE_EMOJI[clamped] ?? "😐"
}

/**
 * Format intensity as a visual indicator (e.g., dots or bars).
 */
export function formatIntensity(intensity: number): string {
  const filled = Math.max(1, Math.min(5, intensity))
  return "●".repeat(filled) + "○".repeat(5 - filled)
}

/**
 * Format a date string for display.
 */
export function formatMemoryDate(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffDays === 0) return "Today"
  if (diffDays === 1) return "Yesterday"
  if (diffDays < 7) return `${diffDays} days ago`
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`
  return date.toLocaleDateString()
}

/**
 * Format confidence as a percentage label.
 */
export function formatConfidence(confidence: number): string {
  if (confidence >= 90) return "Very confident"
  if (confidence >= 70) return "Confident"
  if (confidence >= 50) return "Somewhat sure"
  return "Uncertain"
}

// -----------------------------------------------------------------------------
// Render Memory Summary (for debug panel)
// -----------------------------------------------------------------------------

export interface RenderedMemorySummary {
  /** Total facts stored */
  factCount: number
  /** Total emotions stored */
  emotionCount: number
  /** Formatted fact strings for display */
  recentFacts: Array<{ label: string; value: string }>
  /** Formatted emotion strings for display */
  recentEmotions: Array<{ event: string; tags: string[]; tagClasses: string[] }>
}

/**
 * Render a MemorySummary into display-friendly format.
 */
export function renderMemorySummary(summary: MemorySummary): RenderedMemorySummary {
  return {
    factCount: summary.factual_count,
    emotionCount: summary.emotional_count,
    recentFacts: summary.recent_facts.map((f) => ({
      label: getFactKeyLabel(f.key),
      value: f.value,
    })),
    recentEmotions: summary.recent_emotions.map((e) => ({
      event: e.event,
      tags: e.tags,
      tagClasses: e.tags.map(getEmotionTagClasses),
    })),
  }
}

// -----------------------------------------------------------------------------
// Render Memory Context (for chat prompt display)
// -----------------------------------------------------------------------------

export interface RenderedMemoryContext {
  /** Facts as bullet points */
  factBullets: string[]
  /** Emotions as bullet points */
  emotionBullets: string[]
  /** Habits as bullet points */
  habitBullets: string[]
  /** Whether any memory is available */
  hasMemory: boolean
}

/**
 * Render a MemoryContext into display-friendly format.
 */
export function renderMemoryContext(context: MemoryContext): RenderedMemoryContext {
  return {
    factBullets: context.facts,
    emotionBullets: context.emotions,
    habitBullets: context.habits,
    hasMemory: context.facts.length > 0 || context.emotions.length > 0,
  }
}

// -----------------------------------------------------------------------------
// Memory Chip Components Data
// -----------------------------------------------------------------------------

export interface FactChip {
  key: string
  label: string
  value: string
  confidence: number
  confidenceLabel: string
  dateLabel: string
}

export interface EmotionChip {
  id: string
  event: string
  tags: string[]
  tagClasses: string[]
  valence: number
  valenceEmoji: string
  intensity: number
  intensityDisplay: string
  dateLabel: string
}

/**
 * Convert a FactualMemoryItem to chip display data.
 */
export function factToChip(item: FactualMemoryItem): FactChip {
  return {
    key: item.key,
    label: getFactKeyLabel(item.key),
    value: item.value,
    confidence: item.confidence,
    confidenceLabel: formatConfidence(item.confidence),
    dateLabel: formatMemoryDate(item.last_seen_at),
  }
}

/**
 * Convert an EmotionalMemoryItem to chip display data.
 */
export function emotionToChip(item: EmotionalMemoryItem): EmotionChip {
  return {
    id: item.id,
    event: item.event,
    tags: item.emotion_tags,
    tagClasses: item.emotion_tags.map(getEmotionTagClasses),
    valence: item.valence,
    valenceEmoji: getValenceEmoji(item.valence),
    intensity: item.intensity,
    intensityDisplay: formatIntensity(item.intensity),
    dateLabel: formatMemoryDate(item.occurred_at),
  }
}

// -----------------------------------------------------------------------------
// Debug Panel Helpers
// -----------------------------------------------------------------------------

/**
 * Check if memory debug panel should be shown.
 * Enable via localStorage: localStorage.setItem("DEBUG_MEMORY", "1")
 */
export function isMemoryDebugEnabled(): boolean {
  if (typeof window === "undefined") return false
  return localStorage.getItem("DEBUG_MEMORY") === "1"
}

/**
 * Toggle memory debug panel visibility.
 */
export function toggleMemoryDebug(): void {
  if (typeof window === "undefined") return
  const current = localStorage.getItem("DEBUG_MEMORY")
  if (current === "1") {
    localStorage.removeItem("DEBUG_MEMORY")
  } else {
    localStorage.setItem("DEBUG_MEMORY", "1")
  }
}
