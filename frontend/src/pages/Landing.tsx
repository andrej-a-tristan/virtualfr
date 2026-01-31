import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Heart } from "lucide-react"

export default function Landing() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-b from-background to-background/95 px-6 py-12">
      <div className="mx-auto max-w-2xl space-y-8 text-center">
        <div className="flex justify-center">
          <div className="rounded-2xl bg-primary/10 p-4">
            <Heart className="h-12 w-12 text-primary" />
          </div>
        </div>
        <h1 className="text-4xl font-bold tracking-tight text-foreground md:text-5xl">
          Your companion, your way
        </h1>
        <p className="text-lg text-muted-foreground">
          Create a personalized connection with a unique persona. Dark, premium, and built for adults.
        </p>
        <div className="flex flex-col gap-4 sm:flex-row sm:justify-center">
          <Button asChild size="lg" className="rounded-xl">
            <Link to="/signup">Get started</Link>
          </Button>
          <Button asChild variant="outline" size="lg" className="rounded-xl">
            <Link to="/login">Sign in</Link>
          </Button>
        </div>
      </div>
    </div>
  )
}
