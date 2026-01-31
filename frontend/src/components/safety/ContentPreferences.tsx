import { useState } from "react"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"

export default function ContentPreferences() {
  const [explicit, setExplicit] = useState(true)
  const [notifications, setNotifications] = useState(true)

  return (
    <Card className="rounded-2xl border-white/10">
      <CardHeader>
        <CardTitle>Content preferences</CardTitle>
        <CardDescription>Control what you see and receive.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between">
          <Label htmlFor="explicit" className="cursor-pointer text-sm font-medium">
            Allow explicit content
          </Label>
          <button
            id="explicit"
            type="button"
            role="switch"
            aria-checked={explicit}
            className={cn(
              "relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
              explicit ? "bg-primary" : "bg-muted"
            )}
            onClick={() => setExplicit((v) => !v)}
          >
            <span
              className={cn(
                "pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow ring-0 transition",
                explicit ? "translate-x-5" : "translate-x-1"
              )}
            />
          </button>
        </div>
        <div className="flex items-center justify-between">
          <Label htmlFor="notifications" className="cursor-pointer text-sm font-medium">
            Notifications
          </Label>
          <button
            id="notifications"
            type="button"
            role="switch"
            aria-checked={notifications}
            className={cn(
              "relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
              notifications ? "bg-primary" : "bg-muted"
            )}
            onClick={() => setNotifications((v) => !v)}
          >
            <span
              className={cn(
                "pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow ring-0 transition",
                notifications ? "translate-x-5" : "translate-x-1"
              )}
            />
          </button>
        </div>
      </CardContent>
    </Card>
  )
}
