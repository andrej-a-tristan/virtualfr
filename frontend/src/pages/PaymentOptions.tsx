import { useState } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { getPaymentMethod } from "@/lib/api/endpoints"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { CreditCard, Plus, RefreshCw } from "lucide-react"
import AddCardModal from "@/components/billing/AddCardModal"

const BRAND_ICONS: Record<string, string> = {
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

  const { data, isLoading } = useQuery({
    queryKey: ["paymentMethod"],
    queryFn: getPaymentMethod,
  })

  const handleCardSaved = () => {
    setShowCardModal(false)
    queryClient.invalidateQueries({ queryKey: ["paymentMethod"] })
    queryClient.invalidateQueries({ queryKey: ["billingStatus"] })
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold tracking-tight">Payment Options</h1>
        <Skeleton className="h-40 w-full rounded-2xl" />
      </div>
    )
  }

  const hasCard = data?.has_card ?? false
  const card = data?.card

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Payment Options</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Manage your payment method for subscriptions and gifts
        </p>
      </div>

      <Card className="rounded-2xl border-white/10">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <CreditCard className="h-5 w-5 text-primary" />
            Saved Card
          </CardTitle>
        </CardHeader>
        <CardContent>
          {hasCard && card ? (
            <div className="space-y-4">
              {/* Card display */}
              <div className="flex items-center justify-between rounded-xl border border-white/10 bg-white/5 px-5 py-4">
                <div className="flex items-center gap-4">
                  <div className="flex h-10 w-14 items-center justify-center rounded-lg bg-white/10 text-xs font-bold uppercase tracking-wider text-muted-foreground">
                    {BRAND_ICONS[card.brand] || card.brand}
                  </div>
                  <div>
                    <p className="font-medium">
                      {(BRAND_ICONS[card.brand] || card.brand).charAt(0).toUpperCase() +
                        (BRAND_ICONS[card.brand] || card.brand).slice(1)}{" "}
                      ending in {card.last4}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      Expires {String(card.exp_month).padStart(2, "0")}/{card.exp_year}
                    </p>
                  </div>
                </div>
              </div>

              <Button
                variant="outline"
                className="rounded-xl gap-2"
                onClick={() => setShowCardModal(true)}
              >
                <RefreshCw className="h-4 w-4" />
                Update card
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="rounded-xl border border-dashed border-white/20 px-5 py-8 text-center">
                <CreditCard className="mx-auto h-8 w-8 text-muted-foreground mb-3" />
                <p className="text-sm text-muted-foreground">
                  No card on file
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Add a card to subscribe to plans or send gifts
                </p>
              </div>

              <Button
                className="rounded-xl gap-2"
                onClick={() => setShowCardModal(true)}
              >
                <Plus className="h-4 w-4" />
                Add card
              </Button>
            </div>
          )}
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
