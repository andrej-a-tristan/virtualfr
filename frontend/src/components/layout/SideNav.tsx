import { NavLink } from "react-router-dom"
import { MessageCircle, Image as ImageIcon, User, Settings, CreditCard, Shield } from "lucide-react"
import { cn } from "@/lib/utils"

const links = [
  { to: "/app/chat", label: "Chat", icon: MessageCircle },
  { to: "/app/gallery", label: "Gallery", icon: ImageIcon },
  { to: "/app/profile", label: "Profile", icon: User },
  { to: "/app/settings", label: "Settings", icon: Settings },
  { to: "/app/billing", label: "Billing", icon: CreditCard },
  { to: "/app/safety", label: "Safety", icon: Shield },
]

export default function SideNav() {
  return (
    <aside className="hidden w-56 flex-col border-r border-white/10 bg-card/50 md:flex">
      <nav className="flex flex-1 flex-col gap-1 p-4">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                isActive ? "bg-primary/20 text-primary" : "text-muted-foreground hover:bg-accent hover:text-foreground"
              )
            }
          >
            <Icon className="h-5 w-5" />
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
