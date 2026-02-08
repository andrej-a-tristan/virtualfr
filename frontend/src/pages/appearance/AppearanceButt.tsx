import AppearanceStepPage from "@/components/onboarding/AppearanceStepPage"

export default function AppearanceButt() {
  return (
    <AppearanceStepPage
      title="Butt size?"
      subtitle="Choose her proportions"
      storeKey="butt_size"
      options={["small", "medium", "large", "massive"]}
      promptKey="appearance_butt_size"
      nextRoute="/onboarding/appearance/hair-color"
      backRoute="/onboarding/appearance/breast"
      stepNumber={5}
      totalSteps={9}
    />
  )
}
