import { useQuery } from "@tanstack/react-query"
import { getCurrentGirlfriend } from "@/lib/api/endpoints"
import { useAuth } from "@/lib/hooks/useAuth"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Badge } from "@/components/ui/badge"

export default function Profile() {
  const { user } = useAuth()
  const { data: gf, isLoading } = useQuery({ queryKey: ["girlfriend"], queryFn: getCurrentGirlfriend })

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold tracking-tight">Profile</h1>
        <Skeleton className="h-48 w-full rounded-2xl" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Profile</h1>
      <Card className="rounded-2xl border-white/10">
        <CardHeader className="flex flex-row items-center gap-4">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/20 text-2xl font-semibold text-primary">
            {gf?.display_name?.[0] ?? "?"}
          </div>
          <div>
            <h2 className="text-xl font-semibold">{gf?.display_name ?? "Companion"}</h2>
            <Badge variant="secondary" className="mt-1">Your companion</Badge>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Traits: {gf?.traits ? Object.values(gf.traits).join(", ") : "—"}
          </p>
        </CardContent>
      </Card>
      {user && (
        <Card className="rounded-2xl border-white/10">
          <CardHeader>
            <h2 className="text-lg font-semibold">Account</h2>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p><span className="text-muted-foreground">Email:</span> {user.email}</p>
            {user.display_name && <p><span className="text-muted-foreground">Display name:</span> {user.display_name}</p>}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
