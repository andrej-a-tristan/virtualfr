import AppearanceStepPage from "@/components/onboarding/AppearanceStepPage"

export default function AppearanceEyes() {
  return (
    <AppearanceStepPage
      title="What color are her eyes?"
      subtitle="Choose her eye color"
      storeKey="eye_color"
      options={["brown", "blue", "green", "hazel"]}
      promptKey="appearance_eye_color"
      nextRoute="/onboarding/traits"
      backRoute="/onboarding/appearance/hair-style"
      stepNumber={6}
      totalSteps={7}
    />
  )
}
