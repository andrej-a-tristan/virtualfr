import AppearanceStepPage from "@/components/onboarding/AppearanceStepPage"

export default function AppearanceBreast() {
  return (
    <AppearanceStepPage
      title="Breast size?"
      subtitle="Choose her proportions"
      storeKey="breast_size"
      options={["small", "medium", "large", "massive"]}
      promptKey="appearance_breast_size"
      nextRoute="/onboarding/appearance/butt"
      backRoute="/onboarding/appearance/body"
      stepNumber={4}
      totalSteps={9}
    />
  )
}
