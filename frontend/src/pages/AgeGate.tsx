import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { postAgeGate } from "@/lib/api/endpoints"
import { useQueryClient } from "@tanstack/react-query"
import { useAppStore } from "@/lib/store/useAppStore"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
import { Shield, AlertTriangle } from "lucide-react"

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
      navigate(user?.has_girlfriend ? "/app/girl" : "/onboarding/traits", { replace: true })
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
          <CardTitle className="text-2xl">Age Verification Required</CardTitle>
          <CardDescription className="text-base leading-relaxed">
            This platform contains adult content and is strictly for users aged 18 and over.
            You <span className="font-semibold text-white/80">must</span> confirm your age to continue.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {error && <p className="text-center text-sm text-destructive">{error}</p>}

          {/* Warning notice */}
          <div className="flex items-start gap-3 rounded-lg border border-amber-500/20 bg-amber-500/5 px-4 py-3">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
            <p className="text-xs leading-relaxed text-white/60">
              By checking the box below you confirm that you are at least 18 years old
              and that you consent to viewing adult content. If you are under 18, you must leave this site immediately.
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <Checkbox
              id="age"
              checked={confirmed}
              onChange={(e) => setConfirmed(e.target.checked)}
            />
            <Label htmlFor="age" className="cursor-pointer text-sm font-semibold">
              I confirm that I am 18 years of age or older
            </Label>
          </div>

          <Button
            className="w-full text-base font-semibold"
            size="lg"
            disabled={!confirmed || loading}
            onClick={handleSubmit}
          >
            {loading ? "Verifying…" : "Enter"}
          </Button>

          <p className="text-center text-[11px] text-white/30">
            If you are not 18 or older, please close this page.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
