import AppearanceStepPage from "@/components/onboarding/AppearanceStepPage"

export default function AppearanceHairColor() {
  return (
    <AppearanceStepPage
      title="What color is her hair?"
      subtitle="Choose her hair color"
      storeKey="hair_color"
      options={["black", "brown", "blonde", "red", "ginger", "unnatural"]}
      promptKey="appearance_hair_color"
      nextRoute="/onboarding/appearance/hair-style"
      backRoute="/onboarding/appearance/body"
      stepNumber={4}
      totalSteps={7}
    />
  )
}
