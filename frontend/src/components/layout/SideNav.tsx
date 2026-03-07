import { useState } from "react"
import { NavLink, useNavigate } from "react-router-dom"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import {
  User,
  Settings,
  CreditCard,
  Wallet,
  Shield,
  Sparkles,
  Lock,
  PlusCircle,
  Check,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { getBillingStatus, listGirlfriends, switchGirlfriend } from "@/lib/api/endpoints"
import { useAppStore } from "@/lib/store/useAppStore"
import { useChatStore } from "@/lib/store/useChatStore"
import { Button } from "@/components/ui/button"
import AvatarCircle from "@/components/ui/AvatarCircle"
import UpgradeModal from "@/components/billing/UpgradeModal"

const links = [
  { to: "/app/profile", label: "Profile", icon: User },
  { to: "/app/settings", label: "Settings", icon: Settings },
  { to: "/app/billing", label: "Billing", icon: CreditCard },
  { to: "/app/payment-options", label: "Payment Options", icon: Wallet },
  { to: "/app/safety", label: "Safety", icon: Shield },
]

export default function SideNav() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [upgradeOpen, setUpgradeOpen] = useState(false)

  const { data: billing } = useQuery({
    queryKey: ["billingStatus"],
    queryFn: getBillingStatus,
    retry: false,
  })
  const { data: gfList } = useQuery({
    queryKey: ["girlfriendsList"],
    queryFn: listGirlfriends,
    retry: false,
    staleTime: 10_000,
  })

  const setOnboardingMode = useAppStore((s) => s.setOnboardingMode)
  const clearOnboarding = useAppStore((s) => s.clearOnboarding)
  const currentGirlfriendId = useAppStore((s) => s.currentGirlfriendId)
  const setGirlfriends = useAppStore((s) => s.setGirlfriends)
  const setCurrentGirlfriend = useAppStore((s) => s.setCurrentGirlfriend)
  const setGirlfriend = useAppStore((s) => s.setGirlfriend)
  const resetChat = useChatStore((s) => s.reset)

  const plan = billing?.plan ?? "free"
  const isPaid = plan !== "free"
  const girlfriends = gfList?.girlfriends ?? []
  const girlsMax = billing?.girls_max ?? (isPaid ? 3 : 1)
  const atMax = girlfriends.length >= girlsMax

  const handleSwitch = async (girlfriendId: string) => {
    if (girlfriendId === currentGirlfriendId) {
      // Already selected — just navigate to chat
      navigate("/app/girl")
      return
    }
    try {
      const res = await switchGirlfriend(girlfriendId)
      setGirlfriends(res.girlfriends, res.current_girlfriend_id)
      setCurrentGirlfriend(girlfriendId)
      const selected = res.girlfriends.find((g) => g.id === girlfriendId)
      if (selected) setGirlfriend(selected)
      resetChat()
      queryClient.invalidateQueries({ queryKey: ["girlfriend"] })
      queryClient.invalidateQueries({ queryKey: ["chatHistory"] })
      queryClient.invalidateQueries({ queryKey: ["chatState"] })
      queryClient.invalidateQueries({ queryKey: ["girlfriendsList"] })
      queryClient.invalidateQueries({ queryKey: ["gallery"] })
      navigate("/app/girl")
    } catch {
      // silently fail
    }
  }

  const handleCreateMore = () => {
    if (!isPaid) {
      setUpgradeOpen(true)
      return
    }
    if (atMax) return
    clearOnboarding()
    setOnboardingMode("additional")
    navigate("/onboarding/appearance")
  }

  return (
    <aside className="hidden w-56 flex-col border-r border-white/10 bg-card/50 md:flex">
      {/* ── My Girls section ── */}
      {girlfriends.length > 0 && (
        <div className="border-b border-white/10 px-3 pb-3 pt-4">
          <p className="mb-2 px-1 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            My Girls
          </p>
          <div className="space-y-1">
            {girlfriends.map((g) => {
              const isActive = g.id === currentGirlfriendId
              return (
                <button
                  key={g.id}
                  onClick={() => handleSwitch(g.id)}
                  className={cn(
                    "flex w-full items-center gap-2.5 rounded-lg px-2 py-2 text-left text-sm transition-all",
                    isActive
                      ? "bg-primary/20 text-primary ring-1 ring-primary/30"
                      : "text-muted-foreground hover:bg-accent hover:text-foreground"
                  )}
                >
                  <AvatarCircle
                    name={g.display_name ?? g.name}
                    avatarUrl={g.avatar_url}
                    size="sm"
                  />
                  <span className="flex-1 truncate font-medium">
                    {g.display_name ?? g.name ?? "Girl"}
                  </span>
                  {isActive && <Check className="h-3.5 w-3.5 shrink-0 text-primary" />}
                </button>
              )
            })}
          </div>

          {/* Add new girl button (inline, subtle) */}
          <button
            onClick={handleCreateMore}
            disabled={atMax}
            className={cn(
              "mt-1.5 flex w-full items-center gap-2.5 rounded-lg px-2 py-2 text-left text-sm transition-all",
              atMax
                ? "cursor-not-allowed text-muted-foreground/40"
                : isPaid
                  ? "text-muted-foreground hover:bg-accent hover:text-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-foreground"
            )}
          >
            {isPaid ? (
              <PlusCircle className="h-7 w-7 shrink-0 text-pink-400" />
            ) : (
              <Lock className="h-7 w-7 shrink-0 text-muted-foreground" />
            )}
            <span className="flex-1 truncate font-medium">
              {atMax ? "Max reached" : "New girl"}
            </span>
            {!isPaid && (
              <span className="rounded bg-amber-500/20 px-1.5 py-0.5 text-[10px] font-bold text-amber-400">
                PRO
              </span>
            )}
          </button>
        </div>
      )}

      {/* ── Navigation links ── */}
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

      {/* ── Bottom CTA (prominent gradient button) ── */}
      <div className="p-4 pt-0">
        <Button
          onClick={handleCreateMore}
          disabled={atMax}
          className={cn(
            "relative w-full h-14 rounded-xl font-semibold text-white shadow-lg transition-all",
            "bg-gradient-to-r from-purple-500 via-pink-500 to-rose-500",
            "hover:scale-[1.02] hover:shadow-xl hover:from-purple-600 hover:via-pink-600 hover:to-rose-600",
            "ring-1 ring-white/20",
            "disabled:opacity-60 disabled:hover:scale-100"
          )}
        >
          <div className="flex flex-col items-center gap-0.5">
            <div className="flex items-center gap-2">
              {isPaid ? (
                <Sparkles className="h-4 w-4" />
              ) : (
                <Lock className="h-4 w-4" />
              )}
              <span className="text-sm">
                {atMax ? "Max girls reached" : "Create more girls"}
              </span>
            </div>
            <span className="text-[10px] font-normal opacity-80">
              {isPaid
                ? `${girlfriends.length}/${girlsMax} girls`
                : "Upgrade: up to 3 girls"}
            </span>
          </div>
        </Button>
      </div>

      <UpgradeModal open={upgradeOpen} onClose={() => setUpgradeOpen(false)} />
    </aside>
  )
}
