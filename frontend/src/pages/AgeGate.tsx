import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { postAgeGate } from "@/lib/api/endpoints"
import { useQueryClient } from "@tanstack/react-query"
import { useAppStore } from "@/lib/store/useAppStore"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
import { Shield } from "lucide-react"

export default function AgeGate() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const setUser = useAppStore((s) => s.setUser)
  const user = useAppStore((s) => s.user)
  const [confirmed, setConfirmed] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async () => {
    if (!confirmed) return
    setError(null)
    setLoading(true)
    try {
      await postAgeGate()
      if (user) setUser({ ...user, age_gate_passed: true })
      await queryClient.invalidateQueries({ queryKey: ["me"] })
      navigate(user?.has_girlfriend ? "/app/chat" : "/onboarding/traits", { replace: true })
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-12">
      <Card className="w-full max-w-lg rounded-2xl border-white/10 shadow-xl">
        <CardHeader className="space-y-4 text-center">
          <div className="mx-auto rounded-full bg-amber-500/10 p-4">
            <Shield className="h-12 w-12 text-amber-500" />
          </div>
          <CardTitle className="text-2xl">Age verification</CardTitle>
          <CardDescription className="text-base">
            This service is intended for adults only. You must be 18 years or older to continue.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {error && <p className="text-center text-sm text-destructive">{error}</p>}
          <div className="flex items-center space-x-2">
            <Checkbox
              id="age"
              checked={confirmed}
              onChange={(e) => setConfirmed(e.target.checked)}
            />
            <Label htmlFor="age" className="cursor-pointer text-sm font-medium">
              I confirm that I am 18 years of age or older
            </Label>
          </div>
          <Button
            className="w-full"
            size="lg"
            disabled={!confirmed || loading}
            onClick={handleSubmit}
          >
            {loading ? "Verifying…" : "Continue"}
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
