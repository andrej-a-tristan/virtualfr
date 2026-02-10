import { useState } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Lock, Crown, Eye } from "lucide-react"
import UpgradeModal from "@/components/billing/UpgradeModal"

interface BlurredImageCardProps {
  /** Copy displayed over the blurred image */
  uiCopy: string
  /** URL of the blurred preview image */
  blurredImageUrl?: string
  /** e.g. "free_plan_upgrade" */
  reason?: string
}

export default function BlurredImageCard({
  uiCopy,
  blurredImageUrl,
  reason,
}: BlurredImageCardProps) {
  const [upgradeOpen, setUpgradeOpen] = useState(false)

  return (
    <>
      <div className="flex w-full justify-center py-2">
        <Card className="w-full max-w-sm overflow-hidden rounded-2xl border-pink-500/30 bg-gradient-to-b from-pink-500/10 to-purple-500/10">
          <CardContent className="p-0">
            {/* Blurred image preview */}
            <div className="relative">
              {/* The blurred image */}
              <div className="relative h-64 w-full overflow-hidden bg-gradient-to-br from-pink-900/40 via-purple-900/30 to-slate-900/50">
                {blurredImageUrl ? (
                  <img
                    src={blurredImageUrl}
                    alt=""
                    className="h-full w-full object-cover"
                    style={{ filter: "blur(28px) brightness(0.7) saturate(1.4)", transform: "scale(1.15)" }}
                    loading="lazy"
                  />
                ) : (
                  /* Fallback gradient when no URL */
                  <div className="absolute inset-0 bg-gradient-to-br from-pink-600/30 via-purple-500/25 to-rose-400/20" />
                )}

                {/* Overlay gradient for text readability */}
                <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/30 to-transparent" />

                {/* Lock icon centered */}
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="flex h-16 w-16 items-center justify-center rounded-full bg-white/10 backdrop-blur-md ring-1 ring-white/20">
                    <Lock className="h-7 w-7 text-white/80" />
                  </div>
                </div>

                {/* Peek hint */}
                <div className="absolute bottom-3 left-0 right-0 flex items-center justify-center gap-1.5">
                  <Eye className="h-3 w-3 text-white/50" />
                  <span className="text-[11px] font-medium text-white/50">
                    Premium content
                  </span>
                </div>
              </div>
            </div>

            {/* CTA section */}
            <div className="space-y-3 p-4">
              {/* Message */}
              <p className="text-center text-sm leading-relaxed text-muted-foreground">
                {uiCopy}
              </p>

              {/* Upgrade button */}
              <Button
                className="w-full bg-gradient-to-r from-amber-500 to-pink-500 font-semibold text-white shadow-lg hover:from-amber-600 hover:to-pink-600"
                onClick={() => setUpgradeOpen(true)}
              >
                <Crown className="mr-2 h-4 w-4" />
                Upgrade to Unlock
              </Button>

              {/* Sub-copy */}
              <p className="text-center text-[11px] text-muted-foreground/60">
                Plus starts at €14.99/mo · Cancel anytime
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      <UpgradeModal
        open={upgradeOpen}
        onClose={() => setUpgradeOpen(false)}
        targetPlan="plus"
      />
    </>
  )
}
