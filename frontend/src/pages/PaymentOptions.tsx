import { useState } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { listPaymentMethods, setDefaultCard, deletePaymentMethod } from "@/lib/api/endpoints"
import type { PaymentMethodCardSummary } from "@/lib/api/types"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { CreditCard, Plus, Trash2, Check, CircleDot, Circle } from "lucide-react"
import AddCardModal from "@/components/billing/AddCardModal"

const BRAND_DISPLAY: Record<string, string> = {
  visa: "Visa",
  mastercard: "Mastercard",
  amex: "Amex",
  discover: "Discover",
  diners: "Diners",
  jcb: "JCB",
  unionpay: "UnionPay",
}

export default function PaymentOptions() {
  const queryClient = useQueryClient()
  const [showCardModal, setShowCardModal] = useState(false)
  const [settingDefault, setSettingDefault] = useState<string | null>(null)
  const [deleting, setDeleting] = useState<string | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ["paymentMethods"],
    queryFn: listPaymentMethods,
  })

  const handleCardSaved = () => {
    setShowCardModal(false)
    queryClient.invalidateQueries({ queryKey: ["paymentMethods"] })
    queryClient.invalidateQueries({ queryKey: ["paymentMethod"] })
    queryClient.invalidateQueries({ queryKey: ["billingStatus"] })
  }

  const handleSetDefault = async (card: PaymentMethodCardSummary) => {
    if (card.is_default || settingDefault) return
    setSettingDefault(card.id)
    try {
      await setDefaultCard(card.id)
      await queryClient.invalidateQueries({ queryKey: ["paymentMethods"] })
      await queryClient.invalidateQueries({ queryKey: ["paymentMethod"] })
    } catch {
      // silently fail
    } finally {
      setSettingDefault(null)
    }
  }

  const handleDelete = async (card: PaymentMethodCardSummary) => {
    if (deleting) return
    setDeleting(card.id)
    try {
      await deletePaymentMethod(card.id)
      await queryClient.invalidateQueries({ queryKey: ["paymentMethods"] })
      await queryClient.invalidateQueries({ queryKey: ["paymentMethod"] })
      await queryClient.invalidateQueries({ queryKey: ["billingStatus"] })
    } catch {
      // silently fail
    } finally {
      setDeleting(null)
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold tracking-tight">Payment Options</h1>
        <Skeleton className="h-40 w-full rounded-2xl" />
      </div>
    )
  }

  const cards = data?.cards ?? []

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Payment Options</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Manage your payment cards for subscriptions and gifts
        </p>
      </div>

      <Card className="rounded-2xl border-white/10">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <CreditCard className="h-5 w-5 text-primary" />
            Your Cards
          </CardTitle>
          <CardDescription>
            {cards.length > 0
              ? "Select a card to use for payments. The selected card will be charged for subscriptions and purchases."
              : "Add a card to subscribe to plans or send gifts."}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {cards.map((card) => {
            const brandName = BRAND_DISPLAY[card.brand] || card.brand
            const isSettingThis = settingDefault === card.id
            const isDeletingThis = deleting === card.id

            return (
              <div
                key={card.id}
                className={`flex items-center justify-between rounded-xl border px-4 py-3 transition-all cursor-pointer ${
                  card.is_default
                    ? "border-primary/50 bg-primary/5 shadow-[0_0_10px_rgba(236,72,153,0.1)]"
                    : "border-white/10 bg-white/5 hover:border-white/20"
                }`}
                onClick={() => handleSetDefault(card)}
              >
                <div className="flex items-center gap-3">
                  {/* Selection indicator */}
                  <div className="shrink-0">
                    {card.is_default ? (
                      <CircleDot className="h-5 w-5 text-primary" />
                    ) : isSettingThis ? (
                      <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                    ) : (
                      <Circle className="h-5 w-5 text-muted-foreground/40" />
                    )}
                  </div>

                  {/* Brand logo */}
                  <div className="flex h-9 w-13 items-center justify-center rounded-lg bg-white/10 px-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                    {brandName}
                  </div>

                  {/* Card info */}
                  <div>
                    <p className="text-sm font-medium">
                      •••• {card.last4}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {String(card.exp_month).padStart(2, "0")}/{card.exp_year}
                    </p>
                  </div>

                  {/* Default badge */}
                  {card.is_default && (
                    <span className="ml-2 inline-flex items-center gap-1 rounded-full bg-primary/15 px-2 py-0.5 text-[10px] font-semibold text-primary">
                      <Check className="h-3 w-3" />
                      Active
                    </span>
                  )}
                </div>

                {/* Delete button */}
                <button
                  className="shrink-0 rounded-lg p-2 text-muted-foreground/30 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                  onClick={(e) => {
                    e.stopPropagation()
                    handleDelete(card)
                  }}
                  disabled={isDeletingThis}
                  title="Remove card"
                >
                  {isDeletingThis ? (
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-red-400 border-t-transparent" />
                  ) : (
                    <Trash2 className="h-4 w-4" />
                  )}
                </button>
              </div>
            )
          })}

          {/* Add card button */}
          <Button
            variant="outline"
            className="rounded-xl gap-2 mt-2"
            onClick={() => setShowCardModal(true)}
          >
            <Plus className="h-4 w-4" />
            Add another card
          </Button>
        </CardContent>
      </Card>

      <AddCardModal
        open={showCardModal}
        onClose={() => setShowCardModal(false)}
        onSaved={handleCardSaved}
      />
    </div>
  )
}
