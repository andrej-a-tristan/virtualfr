/**
 * UnifiedPaymentPanel — single reusable payment component for every paid action.
 *
 * Two modes:
 *  A) "Pay with saved card" — one-click; backend charges off_session.
 *  B) "PaymentElement flow" — only if 3DS/SCA required or no saved card.
 *
 * Usage:
 *   <UnifiedPaymentPanel
 *     open={showPayment}
 *     payload={{ type: "gift", product_id: "coffee" }}
 *     title="Buy Gift"
 *     description="Send her a coffee"
 *     amountLabel="€4.99"
 *     onSuccess={(data) => { ... }}
 *     onClose={() => setShowPayment(false)}
 *   />
 */

import { useState, useEffect, useCallback, useRef } from "react"
import { loadStripe, type Stripe } from "@stripe/stripe-js"
import {
  Elements,
  PaymentElement,
  useStripe,
  useElements,
} from "@stripe/react-stripe-js"
import {
  createPaymentIntent,
  confirmPayment,
  getStripePublishableKey,
  type PaymentIntentRequest,
  type PaymentIntentResponse,
} from "@/lib/api/endpoints"
import { Button } from "@/components/ui/button"
import {
  CreditCard,
  Check,
  Loader2,
  X,
  ShieldCheck,
  AlertCircle,
} from "lucide-react"

// ═══════════════════════════════════════════════════════════════════════════
// 3DS / PaymentElement inner form
// ═══════════════════════════════════════════════════════════════════════════

function ConfirmForm({
  isSetup,
  onConfirmed,
  onError,
  amountLabel,
}: {
  isSetup: boolean
  onConfirmed: (paymentMethodId?: string) => void
  onError: (msg: string) => void
  amountLabel?: string
}) {
  const stripe = useStripe()
  const elements = useElements()
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!stripe || !elements) return
    setSubmitting(true)

    if (isSetup) {
      const result = await stripe.confirmSetup({ elements, redirect: "if_required" })
      if (result.error) {
        onError(result.error.message ?? "Setup failed")
        setSubmitting(false)
        return
      }
      const pmId = result.setupIntent?.payment_method as string | undefined
      onConfirmed(pmId)
    } else {
      const result = await stripe.confirmPayment({ elements, redirect: "if_required" })
      if (result.error) {
        onError(result.error.message ?? "Payment failed")
        setSubmitting(false)
        return
      }
      onConfirmed()
    }
    setSubmitting(false)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <PaymentElement options={{ layout: "tabs" }} />
      <Button
        type="submit"
        className="w-full rounded-xl font-semibold"
        disabled={!stripe || !elements || submitting}
      >
        {submitting ? (
          <span className="flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin" />
            Processing...
          </span>
        ) : isSetup ? (
          "Save card"
        ) : (
          amountLabel ? `Pay ${amountLabel}` : "Confirm payment"
        )}
      </Button>
    </form>
  )
}

// ═══════════════════════════════════════════════════════════════════════════
// Main component
// ═══════════════════════════════════════════════════════════════════════════

interface UnifiedPaymentPanelProps {
  open: boolean
  payload: PaymentIntentRequest
  title?: string
  description?: string
  amountLabel?: string
  onSuccess: (data?: Record<string, any>) => void
  onClose: () => void
  /** Skip the modal chrome and just execute payment immediately (for embedded use) */
  autoCharge?: boolean
}

type Phase = "idle" | "charging" | "3ds" | "setup" | "succeeded" | "failed"

export default function UnifiedPaymentPanel({
  open,
  payload,
  title = "Payment",
  description,
  amountLabel,
  onSuccess,
  onClose,
  autoCharge = false,
}: UnifiedPaymentPanelProps) {
  const [activePayload, setActivePayload] = useState<PaymentIntentRequest>(payload)
  const [phase, setPhase] = useState<Phase>("idle")
  const [error, setError] = useState<string | null>(null)
  const [intentResponse, setIntentResponse] = useState<PaymentIntentResponse | null>(null)
  const [stripePromise, setStripePromise] = useState<Promise<Stripe | null> | null>(null)
  const [clientSecret, setClientSecret] = useState<string | null>(null)
  const [isSetup, setIsSetup] = useState(false)
  const didAutoCharge = useRef(false)

  // Reset on close
  useEffect(() => {
    if (!open) {
      setPhase("idle")
      setError(null)
      setIntentResponse(null)
      setStripePromise(null)
      setClientSecret(null)
      setIsSetup(false)
      didAutoCharge.current = false
      setActivePayload(payload)
    }
  }, [open, payload])

  // ── Execute payment ──────────────────────────────────────────────
  const executePayment = useCallback(async (payloadOverride?: PaymentIntentRequest) => {
    const currentPayload = payloadOverride ?? activePayload
    setPhase("charging")
    setError(null)

    try {
      const res = await createPaymentIntent(currentPayload)
      setIntentResponse(res)

      if (res.status === "succeeded") {
        setPhase("succeeded")
        setTimeout(() => onSuccess(res.result_data ?? undefined), 600)
        return
      }

      if (res.status === "no_card" || res.status === "requires_payment_method") {
        let setupSecret = res.setup_intent_client_secret

        // If the backend didn't include a setup intent, request one explicitly.
        if (!setupSecret) {
          try {
            const setupRes = await createPaymentIntent({ type: "setup" })
            setupSecret = setupRes.setup_intent_client_secret
          } catch {
            // Ignore; we'll show a fallback error below.
          }
        }

        if (setupSecret) {
          const { publishable_key } = await getStripePublishableKey()
          setStripePromise(loadStripe(publishable_key))
          setClientSecret(setupSecret)
          setIsSetup(true)
          setPhase("setup")
          return
        }

        setError(res.error || "No card on file. Please add a card in Payment Options.")
        setPhase("failed")
        return
      }

      if (res.status === "requires_action" && res.payment_intent_client_secret) {
        const { publishable_key } = await getStripePublishableKey()
        setStripePromise(loadStripe(publishable_key))
        setClientSecret(res.payment_intent_client_secret)
        setIsSetup(false)
        setPhase("3ds")
        return
      }

      setError(res.error || "Payment failed")
      setPhase("failed")
    } catch (e: any) {
      setError(e?.message || "Something went wrong")
      setPhase("failed")
    }
  }, [activePayload, onSuccess])

  // Auto-charge on open when requested
  useEffect(() => {
    if (open && autoCharge && !didAutoCharge.current && phase === "idle") {
      didAutoCharge.current = true
      executePayment()
    }
  }, [open, autoCharge, phase, executePayment])

  // ── 3DS confirmed ──────────────────────────────────────────────
  const handle3DSConfirmed = useCallback(async () => {
    if (!intentResponse?.payment_intent_id) {
      setPhase("succeeded")
      onSuccess()
      return
    }

    try {
      const res = await confirmPayment({
        payment_intent_id: intentResponse.payment_intent_id,
        type: activePayload.type,
        product_id: activePayload.product_id,
        tier: activePayload.tier,
        girlfriend_id: activePayload.girlfriend_id,
      })

      if (res.status === "succeeded") {
        setPhase("succeeded")
        const merged = {
          ...(intentResponse?.result_data ?? {}),
          ...(res ?? {}),
        }
        setTimeout(() => onSuccess(merged), 600)
      } else {
        setError(res.error || "Payment confirmation failed")
        setPhase("failed")
      }
    } catch (e: any) {
      setError(e?.message || "Confirmation failed")
      setPhase("failed")
    }
  }, [intentResponse, activePayload, onSuccess])

  // ── Setup confirmed (card saved) → retry payment ────────────────
  const handleSetupConfirmed = useCallback(async (pmId?: string) => {
    // Card saved → now execute the original payment
    if (pmId) {
      try {
        const { confirmCard } = await import("@/lib/api/endpoints")
        await confirmCard(pmId)
      } catch { /* webhook handles it */ }
    }
    // If this panel started as setup-only with a target plan, continue into
    // subscription automatically after card save.
    let nextPayload: PaymentIntentRequest | undefined
    if (activePayload.type === "setup" && payload.plan) {
      nextPayload = {
        type: "subscription",
        plan: payload.plan,
        product_id: payload.product_id,
        tier: payload.tier,
        girlfriend_id: payload.girlfriend_id,
        metadata: payload.metadata,
      }
      setActivePayload(nextPayload)
    }

    // Re-run the payment
    setStripePromise(null)
    setClientSecret(null)
    setIsSetup(false)
    didAutoCharge.current = false
    await executePayment(nextPayload)
  }, [executePayment, activePayload.type, payload])

  const handleError = useCallback((msg: string) => {
    setError(msg)
    setPhase("failed")
  }, [])

  if (!open) return null

  const savedLast4 = intentResponse?.saved_card_last4

  return (
    <div className="fixed inset-0 z-[9998] flex items-center justify-center bg-black/60 backdrop-blur-sm px-4">
      <div className="w-full max-w-md rounded-2xl border border-white/10 bg-card p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <CreditCard className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-semibold">{title}</h2>
          </div>
          {phase !== "charging" && phase !== "succeeded" && (
            <button
              onClick={onClose}
              className="rounded-lg p-1 text-muted-foreground hover:text-foreground hover:bg-white/10 transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          )}
        </div>
        {description && <p className="text-sm text-muted-foreground mb-4">{description}</p>}
        {!description && <div className="mb-3" />}

        {/* ── Success state ── */}
        {phase === "succeeded" && (
          <div className="flex flex-col items-center gap-3 py-6 animate-in fade-in duration-300">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-green-500/20">
              <Check className="h-7 w-7 text-green-400" />
            </div>
            <p className="text-base font-semibold">Payment successful!</p>
          </div>
        )}

        {/* ── Idle state — show "Pay with saved card" ── */}
        {phase === "idle" && (
          <div className="space-y-4">
            {amountLabel && (
              <div className="text-center py-2">
                <p className="text-2xl font-bold">{amountLabel}</p>
              </div>
            )}

            <Button
              className="w-full rounded-xl font-semibold gap-2 bg-gradient-to-r from-pink-500 via-amber-400 to-pink-500 bg-[length:200%_100%] animate-[shimmer_2s_linear_infinite] text-white shadow-lg"
              onClick={executePayment}
            >
              <CreditCard className="h-4 w-4" />
              Pay now
            </Button>

            <div className="flex items-start gap-2 rounded-lg bg-white/5 p-3">
              <ShieldCheck className="h-4 w-4 mt-0.5 shrink-0 text-primary" />
              <p className="text-xs text-muted-foreground leading-relaxed">
                Payment is processed securely via Stripe. No redirects — everything stays in-app.
              </p>
            </div>
          </div>
        )}

        {/* ── Charging state ── */}
        {phase === "charging" && (
          <div className="flex flex-col items-center gap-3 py-8">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            <p className="text-sm text-muted-foreground">
              {savedLast4
                ? `Charging card ending in ${savedLast4}...`
                : "Processing payment..."}
            </p>
          </div>
        )}

        {/* ── 3DS / PaymentElement state ── */}
        {(phase === "3ds" || phase === "setup") && stripePromise && clientSecret && (
          <div className="space-y-3">
            {phase === "3ds" && (
              <p className="text-sm text-muted-foreground text-center">
                Additional authentication required by your bank.
              </p>
            )}
            {phase === "setup" && (
              <p className="text-sm text-muted-foreground text-center">
                Add a card to continue.
              </p>
            )}
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
              <ConfirmForm
                isSetup={isSetup}
                onConfirmed={isSetup ? handleSetupConfirmed : handle3DSConfirmed}
                onError={handleError}
                amountLabel={amountLabel}
              />
            </Elements>
          </div>
        )}

        {/* ── Failed state ── */}
        {phase === "failed" && (
          <div className="space-y-4">
            <div className="flex flex-col items-center gap-3 py-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-500/15">
                <AlertCircle className="h-6 w-6 text-red-400" />
              </div>
              <p className="text-sm text-red-300 text-center">{error || "Payment failed"}</p>
            </div>
            <div className="flex gap-3">
              <Button variant="outline" className="flex-1 rounded-xl" onClick={onClose}>
                Cancel
              </Button>
              <Button className="flex-1 rounded-xl" onClick={() => { setPhase("idle"); setError(null) }}>
                Try again
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
