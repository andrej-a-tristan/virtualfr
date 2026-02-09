import { useState } from "react"
import type { BillingStatus } from "@/lib/api/types"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Sparkles, Info } from "lucide-react"
import UpgradeModal from "@/components/billing/UpgradeModal"

interface PaywallInlineCardProps {
  billing: BillingStatus
}

export default function PaywallInlineCard({ billing }: PaywallInlineCardProps) {
  const [upgradeOpen, setUpgradeOpen] = useState(false)

  // Determine best upgrade target based on current plan
  const targetPlan = billing.plan === "free" ? "plus" : "premium"

  return (
    <>
      <Card className="rounded-xl border-primary/30 bg-primary/5">
        <CardContent className="p-3 space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-primary" />
              <span className="text-sm text-muted-foreground">
                Free plan: {billing.message_cap} messages, {billing.image_cap} images. Upgrade for more.
              </span>
            </div>
            <Button size="sm" variant="default" onClick={() => setUpgradeOpen(true)}>
              Upgrade
            </Button>
          </div>
          <div className="flex items-start gap-1.5">
            <Info className="h-3 w-3 mt-0.5 shrink-0 text-muted-foreground/60" />
            <p className="text-[11px] text-muted-foreground/60">
              Upgrades are prorated: unused time on your current plan is credited.
            </p>
          </div>
        </CardContent>
      </Card>

      <UpgradeModal
        open={upgradeOpen}
        onClose={() => setUpgradeOpen(false)}
        targetPlan={targetPlan}
      />
    </>
  )
}
