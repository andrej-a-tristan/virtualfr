import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import ReportDialog from "@/components/safety/ReportDialog"
import ContentPreferences from "@/components/safety/ContentPreferences"
import { Shield } from "lucide-react"

export default function Safety() {
  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold tracking-tight">Safety</h1>
      <Card className="rounded-2xl border-white/10">
        <CardHeader className="flex flex-row items-center gap-2">
          <Shield className="h-5 w-5 text-primary" />
          <CardTitle>Report & moderation</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <CardDescription>
            If you see content that violates our guidelines, you can report it. We take all reports seriously.
          </CardDescription>
          <ReportDialog />
        </CardContent>
      </Card>
      <ContentPreferences />
    </div>
  )
}
