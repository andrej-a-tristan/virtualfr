import { useNavigate } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { getCurrentGirlfriend } from "@/lib/api/endpoints"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import PersonaPreviewCard from "@/components/onboarding/PersonaPreviewCard"
import type { TraitsInput } from "@/lib/api/zod"

export default function PersonaPreview() {
  const navigate = useNavigate()
  const { data: gf, isLoading } = useQuery({ queryKey: ["girlfriend"], queryFn: getCurrentGirlfriend })

  if (isLoading) {
    return (
      <div className="mx-auto max-w-md space-y-6 px-4 py-12">
        <Skeleton className="h-12 w-48" />
        <Skeleton className="h-64 w-full rounded-2xl" />
        <Skeleton className="h-10 w-full" />
      </div>
    )
  }

  if (!gf) {
    navigate("/onboarding/traits", { replace: true })
    return null
  }

  const traits = gf.traits as Partial<TraitsInput>

  return (
    <div className="mx-auto max-w-md space-y-8 px-4 py-12">
      <div className="text-center">
        <h1 className="text-2xl font-bold tracking-tight">Meet {gf.name}</h1>
        <p className="mt-2 text-muted-foreground">Your companion is ready.</p>
      </div>
      <Card className="overflow-hidden rounded-2xl border-white/10">
        {gf.avatar_url && (
          <div className="aspect-square w-full bg-muted">
            <img src={gf.avatar_url} alt={gf.name} className="h-full w-full object-cover" />
          </div>
        )}
        <CardHeader>
          <h2 className="text-xl font-semibold">{gf.name}</h2>
        </CardHeader>
        <CardContent>
          <PersonaPreviewCard traits={traits} />
        </CardContent>
      </Card>
      <Button className="w-full" size="lg" onClick={() => navigate("/app/chat", { replace: true })}>
        Start chatting
      </Button>
    </div>
  )
}
