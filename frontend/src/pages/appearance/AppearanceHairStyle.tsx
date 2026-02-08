import AppearanceStepPage from "@/components/onboarding/AppearanceStepPage"

export default function AppearanceHairStyle() {
  return (
    <AppearanceStepPage
      title="What's her hair style?"
      subtitle="Choose how she wears it"
      storeKey="hair_style"
      options={["long", "bob", "curly", "straight", "bun"]}
      promptKey="appearance_hair_style"
      nextRoute="/onboarding/appearance/eyes"
      backRoute="/onboarding/appearance/hair-color"
      stepNumber={5}
      totalSteps={7}
    />
  )
}
