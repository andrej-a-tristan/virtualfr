import AppearanceStepPage from "@/components/onboarding/AppearanceStepPage"

export default function AppearanceAge() {
  return (
    <AppearanceStepPage
      title="How old does she look?"
      subtitle="Choose her apparent age range"
      storeKey="age_range"
      options={["18", "19-21", "22-26", "27+"]}
      promptKey="appearance_age_range"
      nextRoute="/onboarding/appearance/ethnicity"
      backRoute="/onboarding/appearance"
      stepNumber={1}
      totalSteps={5}
      columns={4}
    />
  )
}
