import type { BillingStatus } from "@/lib/api/types"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { checkout } from "@/lib/api/endpoints"
import { Sparkles } from "lucide-react"

interface PaywallInlineCardProps {
  billing: BillingStatus
}

export default function PaywallInlineCard({ billing }: PaywallInlineCardProps) {
  const handleUpgrade = async () => {
    const res = await checkout()
    if (res.checkout_url) window.open(res.checkout_url, "_blank")
  }

  return (
    <Card className="rounded-xl border-primary/30 bg-primary/5">
      <CardContent className="flex flex-wrap items-center justify-between gap-3 p-3">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-primary" />
          <span className="text-sm text-muted-foreground">
            Free plan: {billing.message_cap} messages, {billing.image_cap} images. Upgrade for more.
          </span>
        </div>
        <Button size="sm" variant="default" onClick={handleUpgrade}>
          Upgrade
        </Button>
      </CardContent>
    </Card>
  )
}
