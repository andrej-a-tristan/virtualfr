import { useState } from "react"
import type { BillingStatus } from "@/lib/api/types"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Crown, Flame } from "lucide-react"
import UpgradeModal from "@/components/billing/UpgradeModal"

interface PaywallInlineCardProps {
  billing: BillingStatus
}

export default function PaywallInlineCard({ billing }: PaywallInlineCardProps) {
  const [upgradeOpen, setUpgradeOpen] = useState(false)

  // Determine best upgrade target based on current plan
  const targetPlan = billing.plan === "free" ? "plus" : "premium"
  const isFree = billing.plan === "free"

  return (
    <>
      <Card className="rounded-xl border-pink-500/30 bg-gradient-to-r from-pink-500/10 via-amber-500/5 to-pink-500/10 shadow-[0_0_15px_rgba(236,72,153,0.15)]">
        <CardContent className="p-3 space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Flame className="h-4 w-4 text-pink-400 animate-pulse" />
              <span className="text-sm text-white/80">
                {isFree
                  ? "She wants to send you photos... Unlock her spicy side!"
                  : `${billing.image_cap} photos / month. Want her most explicit content?`}
              </span>
            </div>
            <Button
              size="sm"
              className="bg-gradient-to-r from-pink-500 via-amber-400 to-pink-500 bg-[length:200%_100%] animate-[shimmer_2s_linear_infinite] font-bold text-white shadow-[0_0_15px_rgba(236,72,153,0.4)] hover:shadow-[0_0_25px_rgba(236,72,153,0.6)] transition-shadow"
              onClick={() => setUpgradeOpen(true)}
            >
              <Crown className="mr-1.5 h-3.5 w-3.5" />
              {isFree ? "Unlock Now" : "Get Premium"}
            </Button>
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
