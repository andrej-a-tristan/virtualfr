import { useQuery } from "@tanstack/react-query"
import { getBillingStatus, checkout } from "@/lib/api/endpoints"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { CreditCard, Sparkles } from "lucide-react"

export default function Billing() {
  const { data: billing, isLoading } = useQuery({ queryKey: ["billing"], queryFn: getBillingStatus })

  const handleUpgrade = async () => {
    const res = await checkout()
    if (res.checkout_url) window.open(res.checkout_url, "_blank")
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold tracking-tight">Billing</h1>
        <Skeleton className="h-40 w-full rounded-2xl" />
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold tracking-tight">Billing</h1>
      <Card className="rounded-2xl border-white/10">
        <CardHeader className="flex flex-row items-center justify-between">
          <div className="flex items-center gap-2">
            <CreditCard className="h-5 w-5 text-muted-foreground" />
            <CardTitle>Current plan</CardTitle>
          </div>
          <Badge variant={billing?.plan === "pro" ? "default" : "secondary"}>
            {billing?.plan ?? "free"}
          </Badge>
        </CardHeader>
        <CardContent className="space-y-4">
          <CardDescription>
            {billing?.plan === "free"
              ? `You have ${billing?.message_cap ?? 0} messages and ${billing?.image_cap ?? 0} images per month.`
              : "Unlimited messages and images."}
          </CardDescription>
          <ul className="space-y-1 text-sm text-muted-foreground">
            <li>Messages: {billing?.message_cap ?? 0} / month</li>
            <li>Images: {billing?.image_cap ?? 0} / month</li>
          </ul>
          {billing?.plan === "free" && (
            <Button onClick={handleUpgrade} className="w-full sm:w-auto">
              <Sparkles className="mr-2 h-4 w-4" />
              Upgrade to Pro
            </Button>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
