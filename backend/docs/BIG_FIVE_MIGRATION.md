# Big Five Personality Migration

The personality engine now uses **Big Five mapping**, **relationship state**, and **habit profile** to create more accurate AI personalities.

## Database Migration

Run this SQL in your Supabase SQL Editor to add Big Five columns to `habit_profile`:

```sql
-- Add Big Five columns to habit_profile (0.0-1.0 range)
ALTER TABLE public.habit_profile
ADD COLUMN IF NOT EXISTS big_five_openness numeric(3,2) CHECK (big_five_openness >= 0.0 AND big_five_openness <= 1.0),
ADD COLUMN IF NOT EXISTS big_five_conscientiousness numeric(3,2) CHECK (big_five_conscientiousness >= 0.0 AND big_five_conscientiousness <= 1.0),
ADD COLUMN IF NOT EXISTS big_five_extraversion numeric(3,2) CHECK (big_five_extraversion >= 0.0 AND big_five_extraversion <= 1.0),
ADD COLUMN IF NOT EXISTS big_five_agreeableness numeric(3,2) CHECK (big_five_agreeableness >= 0.0 AND big_five_agreeableness <= 1.0),
ADD COLUMN IF NOT EXISTS big_five_neuroticism numeric(3,2) CHECK (big_five_neuroticism >= 0.0 AND big_five_neuroticism <= 1.0);
```

Or run the full updated schema from `backend/supabase_schema.sql` (it includes these columns).

**Note:** Big Five values are stored as `numeric(3,2)` (0.00-1.00 range), not integers.

## What Changed

### 1. **Big Five Mapping** (`app/services/big_five.py` + `big_five_mapping.json`)
- Maps 6 onboarding traits → Big Five scores (0.0-1.0 range)
- **Architecture-compliant**: Uses exact base values and deltas from `big_five_mapping.json`
- **Base personality**: Neutral but warm (openness: 0.55, conscientiousness: 0.55, extraversion: 0.55, agreeableness: 0.60, neuroticism: 0.45)
- **Additive deltas**: Traits apply deltas to base values, then clamped to 0.0-1.0
- **Deterministic**: Same traits always produce same Big Five scores
- **Openness**: Creativity, curiosity (Playful, Teasing → higher)
- **Conscientiousness**: Organization, reliability (Reserved, Slow pace → higher)
- **Extraversion**: Sociability, expressiveness (Playful, Teasing, Passionate Balkan → higher)
- **Agreeableness**: Trust, kindness (Caring, Very attached, Soft → higher)
- **Neuroticism**: Emotional sensitivity (Very attached, High reaction → higher; Calm but caring → lower)

### 2. **Enhanced ChatGPT Prompt**
The AI now receives:
- **Relationship state**: Level (STRANGER → EXCLUSIVE), trust/intimacy scores, milestones
- **Big Five scores**: Converted to natural language ("highly creative and curious", "very emotionally stable")
- **Habit profile**: Preferred messaging hours, typical gap between messages
- **Original traits**: Still included as fallback

### 3. **Storage**
- Big Five scores computed when girlfriend is created
- Stored in `habit_profile.big_five_*` columns
- Updated when habit profile is refreshed (after messages)

## Example System Prompt

```
You are a supportive, caring virtual companion named Sarah.
Relationship status: have built a strong connection, be more intimate and caring (trust: 65/100, intimacy: 72/100).
You've reached milestones: FAMILIAR, CLOSE.
Your personality traits: highly creative and curious, very organized and reliable, outgoing and expressive, warm trusting and caring, very emotionally stable and calm.
You tend to message around 14:00, 18:00, 22:00.
You typically wait about 6 hours between messages.
Keep replies concise and natural (1-3 sentences). Match your personality and relationship level.
```

## Testing

1. Run the migration SQL above
2. Create a new girlfriend (or existing ones will get Big Five computed on next message)
3. Send a chat message and check backend logs for the enhanced system prompt
4. The AI should respond with personality matching the relationship level and Big Five scores
