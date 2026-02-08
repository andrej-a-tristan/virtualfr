import { useState, useEffect, useCallback } from "react"
import { loadStripe, type Stripe } from "@stripe/stripe-js"
import {
  Elements,
  PaymentElement,
  useStripe,
  useElements,
} from "@stripe/react-stripe-js"
import { createSetupIntent, confirmCard } from "@/lib/api/endpoints"
import { Button } from "@/components/ui/button"
import { CreditCard, ShieldCheck, X } from "lucide-react"

// Plan display info for the modal
const PLAN_INFO: Record<string, { name: string; price: string }> = {
  plus: { name: "Plus", price: "€14.99/month" },
  premium: { name: "Premium", price: "€29.99/month" },
}

// ── Inner form (rendered inside <Elements>) ─────────────────────────────────

function CardForm({
  onSaved,
  onCancel,
  plan,
}: {
  onSaved: () => void
  onCancel: () => void
  plan?: string
}) {
  const stripe = useStripe()
  const elements = useElements()
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const isPaid = plan === "plus" || plan === "premium"
  const planInfo = plan ? PLAN_INFO[plan] : undefined

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!stripe || !elements) return

    setSubmitting(true)
    setError(null)

    const result = await stripe.confirmSetup({
      elements,
      redirect: "if_required",
    })

    if (result.error) {
      setError(result.error.message ?? "Something went wrong")
      setSubmitting(false)
      return
    }

    // Tell backend the card is saved with the payment method ID
    const paymentMethodId = result.setupIntent?.payment_method as string | undefined
    try {
      await confirmCard(paymentMethodId)
    } catch {
      // non-critical, webhook will handle it
    }

    setSubmitting(false)
    onSaved()
  }

  const submitLabel = submitting
    ? "Processing…"
    : isPaid
      ? `Subscribe – ${planInfo?.price}`
      : "Save card"

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <PaymentElement options={{ layout: "tabs" }} />

      {error && (
        <p className="text-sm text-destructive text-center">{error}</p>
      )}

      {plan === "free" && (
        <div className="flex items-start gap-2 rounded-lg bg-white/5 p-3">
          <ShieldCheck className="h-4 w-4 mt-0.5 shrink-0 text-primary" />
          <p className="text-xs text-muted-foreground leading-relaxed">
            You won&apos;t be charged unless you upgrade. We require a card to
            reveal your companion&apos;s image and prevent abuse.
          </p>
        </div>
      )}

      <div className="flex gap-3">
        <Button
          type="button"
          variant="outline"
          className="flex-1 rounded-xl"
          onClick={onCancel}
          disabled={submitting}
        >
          Cancel
        </Button>
        <Button
          type="submit"
          className="flex-1 rounded-xl"
          disabled={!stripe || !elements || submitting}
        >
          {submitLabel}
        </Button>
      </div>
    </form>
  )
}

// ── Outer modal ─────────────────────────────────────────────────────────────

interface AddCardModalProps {
  open: boolean
  onClose: () => void
  onSaved: () => void
  plan?: string
}

export default function AddCardModal({ open, onClose, onSaved, plan }: AddCardModalProps) {
  const [stripePromise, setStripePromise] = useState<Promise<Stripe | null> | null>(null)
  const [clientSecret, setClientSecret] = useState<string | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const isPaid = plan === "plus" || plan === "premium"
  const planInfo = plan ? PLAN_INFO[plan] : undefined

  const init = useCallback(async () => {
    setLoading(true)
    setLoadError(null)
    try {
      const { client_secret, publishable_key } = await createSetupIntent()
      setStripePromise(loadStripe(publishable_key))
      setClientSecret(client_secret)
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : "Failed to initialize")
    } finally {
      setLoading(false)
    }
  }, [])

  // Reset state when modal closes, so re-opening starts fresh
  useEffect(() => {
    if (!open) {
      setStripePromise(null)
      setClientSecret(null)
      setLoadError(null)
      setLoading(false)
    }
  }, [open])

  // Auto-init when modal opens
  useEffect(() => {
    if (open && !clientSecret && !loading && !loadError) {
      init()
    }
  }, [open, clientSecret, loading, loadError, init])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4">
      <div className="w-full max-w-md rounded-2xl border border-white/10 bg-card p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <CreditCard className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-semibold">
              {isPaid ? `Subscribe to ${planInfo?.name}` : "Add payment card"}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1 text-muted-foreground hover:text-foreground hover:bg-white/10 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Subheading for paid plans */}
        {isPaid && planInfo && (
          <p className="text-sm text-muted-foreground mb-5">
            {planInfo.price} — your card will be charged now.
          </p>
        )}
        {!isPaid && <div className="mb-4" />}

        {/* Content */}
        {loading && (
          <div className="flex flex-col items-center gap-3 py-8">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            <p className="text-sm text-muted-foreground">Loading payment form…</p>
          </div>
        )}

        {loadError && (
          <div className="space-y-3 py-4">
            <p className="text-sm text-destructive text-center">{loadError}</p>
            <Button variant="outline" className="w-full rounded-xl" onClick={init}>
              Retry
            </Button>
          </div>
        )}

        {stripePromise && clientSecret && !loading && (
          <Elements
            stripe={stripePromise}
            options={{
              clientSecret,
              appearance: {
                theme: "night",
                variables: {
                  colorPrimary: "#e0458b",
                  colorBackground: "#1a1a2e",
                  colorText: "#e0e0e0",
                  borderRadius: "10px",
                  fontFamily: "system-ui, sans-serif",
                },
              },
            }}
          >
            <CardForm onSaved={onSaved} onCancel={onClose} plan={plan} />
          </Elements>
        )}
      </div>
    </div>
  )
}
