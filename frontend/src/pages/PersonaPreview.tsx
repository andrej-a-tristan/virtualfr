import { useNavigate } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { getCurrentGirlfriend } from "@/lib/api/endpoints"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import PersonaPreviewCard from "@/components/onboarding/PersonaPreviewCard"
import type { TraitSelection } from "@/lib/api/types"
import { Sparkles } from "lucide-react"

export default function PersonaPreview() {
  const navigate = useNavigate()
  const { data: gf, isLoading } = useQuery({
    queryKey: ["girlfriend"],
    queryFn: getCurrentGirlfriend,
  })

  if (isLoading) {
    return (
      <div className="mx-auto max-w-lg space-y-6 px-4 py-12">
        <Skeleton className="h-10 w-48" />
        <Skeleton className="h-64 w-full rounded-2xl" />
        <Skeleton className="h-12 w-full rounded-xl" />
      </div>
    )
  }

  if (!gf) {
    navigate("/onboarding/traits", { replace: true })
    return null
  }

  const traits = gf.traits as Partial<TraitSelection>
  const girlfriendName = gf.display_name || gf.name || "Your Companion"

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-background/95">
      <div className="mx-auto max-w-lg space-y-8 px-4 py-12">
        <div className="text-center">
          <h1 className="text-2xl font-bold tracking-tight text-foreground md:text-3xl">
            Meet {girlfriendName}
          </h1>
          <p className="mt-2 text-muted-foreground">
            Your companion is ready. She’ll open up more as you get closer.
          </p>
        </div>

        <PersonaPreviewCard displayName={girlfriendName} traits={traits} />

        <Card className="rounded-2xl border-primary/20 bg-primary/5">
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              <h2 className="text-base font-semibold text-foreground">
                What to expect
              </h2>
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            <p className="text-sm text-muted-foreground">
              Her personality stays consistent, but she opens up more as you get closer. Start chatting to build your connection.
            </p>
          </CardContent>
        </Card>

        <Button
          className="w-full rounded-xl"
          size="lg"
          onClick={() => navigate("/app/girl", { replace: true })}
        >
          Start Chat
        </Button>
      </div>
    </div>
  )
}
