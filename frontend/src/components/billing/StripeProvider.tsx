import { useEffect, useState } from "react"
import { Elements } from "@stripe/react-stripe-js"
import { loadStripe, type Stripe } from "@stripe/stripe-js"
import { getStripePublishableKey } from "@/lib/api/endpoints"

export default function StripeProvider({ children }: { children: React.ReactNode }) {
  const [stripePromise, setStripePromise] = useState<Promise<Stripe | null> | null>(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const { publishable_key } = await getStripePublishableKey()
        if (!cancelled) {
          setStripePromise(loadStripe(publishable_key))
        }
      } catch {
        if (!cancelled) {
          setStripePromise(null)
        }
      }
    })()

    return () => {
      cancelled = true
    }
  }, [])

  if (!stripePromise) return <>{children}</>

  return (
    <Elements stripe={stripePromise}>
      {children}
    </Elements>
  )
}

