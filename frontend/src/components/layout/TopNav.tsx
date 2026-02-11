import { Link, useNavigate } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { getBillingStatus } from "@/lib/api/endpoints"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { useAuth } from "@/lib/hooks/useAuth"
import { User, LogOut } from "lucide-react"

export default function TopNav() {
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const { data: billing } = useQuery({ queryKey: ["billingStatus"], queryFn: getBillingStatus })

  return (
    <header className="sticky top-0 z-40 flex h-14 items-center justify-between border-b border-white/10 bg-background/80 px-4 backdrop-blur-sm md:px-6">
      <Link to="/app/girl" className="flex items-center gap-2 font-semibold tracking-tight text-foreground">
        <span className="text-lg">Companion</span>
      </Link>
      <div className="flex items-center gap-3">
        {billing && (
          <Badge
            variant={billing.plan !== "free" ? "default" : "secondary"}
            className={`text-xs capitalize ${
              billing.plan === "premium"
                ? "bg-amber-500/20 text-amber-300 border-amber-500/30"
                : billing.plan === "plus"
                  ? "bg-primary/20 text-primary border-primary/30"
                  : ""
            }`}
          >
            {billing.plan}
          </Badge>
        )}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="rounded-full">
              <User className="h-5 w-5" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            <div className="px-2 py-1.5 text-sm text-muted-foreground">{user?.email}</div>
            <DropdownMenuItem asChild>
              <Link to="/app/profile">Profile</Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link to="/app/settings">Settings</Link>
            </DropdownMenuItem>
            <DropdownMenuItem onClick={async () => { await logout(); navigate("/login", { replace: true }); }}>
              <LogOut className="mr-2 h-4 w-4" />
              Log out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}
