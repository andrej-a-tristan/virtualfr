import AppearanceStepPage from "@/components/onboarding/AppearanceStepPage"

export default function AppearanceBody() {
  return (
    <AppearanceStepPage
      title="What's her body type?"
      subtitle="Choose her figure"
      storeKey="body_type"
      options={["slim", "athletic", "curvy"]}
      promptKey="appearance_body_type"
      nextRoute="/onboarding/appearance/breast"
      backRoute="/onboarding/appearance/ethnicity"
      stepNumber={3}
      totalSteps={9}
    />
  )
}
