import { useNavigate } from "react-router-dom"
import { useAuth } from "@/lib/hooks/useAuth"
import { Button } from "@/components/ui/button"
import ContentPreferences from "@/components/safety/ContentPreferences"
import { LogOut } from "lucide-react"

export default function Settings() {
  const { logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate("/", { replace: true })
  }

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
      <ContentPreferences />
      <div className="flex">
        <Button variant="outline" onClick={handleLogout}>
          <LogOut className="mr-2 h-4 w-4" />
          Log out
        </Button>
      </div>
    </div>
  )
}
