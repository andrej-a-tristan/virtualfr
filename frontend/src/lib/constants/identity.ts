/** Identity onboarding constants */

export const JOB_VIBES = [
  { id: "student", title: "Student", subtitle: "late-night study dates" },
  { id: "barista", title: "Barista / café girl", subtitle: "warm café energy" },
  { id: "creative", title: "Creative (artist / designer)", subtitle: "soft artsy muse" },
  { id: "tech", title: "Tech (developer / gamer-adjacent)", subtitle: "smart + playful" },
  { id: "healthcare", title: "Healthcare (nurse / caregiver)", subtitle: "gentle caretaker" },
  { id: "fitness", title: "Fitness (trainer / wellness)", subtitle: "motivating, healthy vibe" },
  { id: "corporate", title: "Corporate (office / business)", subtitle: "ambitious office baddie" },
  { id: "entrepreneur", title: "Entrepreneur (startup / hustle)", subtitle: "builder energy" },
  { id: "teacher", title: "Teacher / mentor", subtitle: "patient and supportive" },
  { id: "nightlife", title: "Nightlife (DJ / events)", subtitle: "electric nights" },
  { id: "hospitality", title: "Hospitality (travel / hotels)", subtitle: "friendly, social" },
  { id: "in-between", title: "In-between (figuring it out)", subtitle: "finding her path" },
] as const

export const HOBBIES = [
  "Cooking / baking",
  "Gym / strength",
  "Yoga / pilates",
  "Hiking / nature walks",
  "Reading / booktok vibes",
  "Movies / series",
  "Gaming",
  "Photography",
  "Music (singing / playlists)",
  "Dancing",
  "Art / drawing",
  "Fashion / styling",
  "Travel / city exploring",
  "Cafés / coffee walks",
  "Language learning",
  "Journaling / self-care",
  "Gardening / plants",
  "Volunteering / charity",
] as const

export const CITY_VIBES = [
  { id: "cozy-european", title: "Cozy European city" },
  { id: "big-city", title: "Big city energy" },
  { id: "beach-town", title: "Beach town" },
  { id: "mountain", title: "Mountain / outdoors" },
  { id: "suburban", title: "Suburban calm" },
  { id: "artsy", title: "Artsy neighborhood" },
  { id: "countryside", title: "Quiet countryside" },
  { id: "nightlife-district", title: "Nightlife district" },
] as const

export const SAFE_NAMES = [
  "Luna", "Aria", "Maya", "Chloe", "Ivy", "Stella", "Nora", "Lily",
  "Sophie", "Mia", "Zoe", "Ella", "Ruby", "Violet", "Hazel", "Aurora",
  "Willow", "Jade", "Iris", "Scarlett", "Sienna", "Freya", "Ember", "Sage",
  "Clara", "Elise", "Nina", "Vera", "Alice", "Eva", "Lena", "Rosa",
  "Daisy", "Fern", "Pearl", "Nova", "Coral", "Wren", "Skye", "June",
  "Mika", "Yuki", "Sana", "Hana", "Emi", "Rei", "Kira", "Lila",
  "Tessa", "Greta",
] as const

/** Validate name: letters (unicode), spaces, hyphens, apostrophes, 1-20 chars */
export function isValidName(name: string): boolean {
  const trimmed = name.trim()
  if (trimmed.length < 1 || trimmed.length > 20) return false
  // Unicode letters, spaces, hyphens, apostrophes
  return /^[\p{L} '\-]+$/u.test(trimmed)
}

export function getRandomName(): string {
  return SAFE_NAMES[Math.floor(Math.random() * SAFE_NAMES.length)]
}
