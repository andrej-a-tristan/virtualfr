import AppearanceStepPage from "@/components/onboarding/AppearanceStepPage"

export default function AppearanceEthnicity() {
  return (
    <AppearanceStepPage
      title="What's her ethnicity?"
      subtitle="Choose her look"
      storeKey="ethnicity"
      options={["any", "asian", "black", "latina", "white", "middle-eastern", "south-asian"]}
      promptKey="appearance_ethnicity"
      nextRoute="/onboarding/appearance/body"
      backRoute="/onboarding/appearance/age"
      stepNumber={2}
      totalSteps={5}
      columns={4}
    />
  )
}
