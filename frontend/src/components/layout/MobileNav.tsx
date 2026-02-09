import { NavLink } from "react-router-dom"
import { Heart, User, Settings } from "lucide-react"
import { cn } from "@/lib/utils"

const links = [
  { to: "/app/girl", label: "My Girl", icon: Heart },
  { to: "/app/profile", label: "Profile", icon: User },
  { to: "/app/settings", label: "Settings", icon: Settings },
]

export default function MobileNav() {
  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 flex items-center justify-around border-t border-white/10 bg-card/95 py-2 backdrop-blur md:hidden">
      {links.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            cn(
              "flex flex-col items-center gap-1 rounded-lg px-4 py-2 text-xs font-medium transition-colors",
              isActive ? "text-primary" : "text-muted-foreground"
            )
          }
        >
          <Icon className="h-6 w-6" />
          {label}
        </NavLink>
      ))}
    </nav>
  )
}
