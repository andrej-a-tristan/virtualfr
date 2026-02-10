import { useQuery, useQueryClient } from "@tanstack/react-query"
import { getCurrentGirlfriend, getBillingStatus, listGirlfriends, switchGirlfriend } from "@/lib/api/endpoints"
import { Skeleton } from "@/components/ui/skeleton"
import { Sparkles, Crown, Heart, ChevronDown, Check, Users } from "lucide-react"
import AvatarCircle from "@/components/ui/AvatarCircle"
import { useAppStore } from "@/lib/store/useAppStore"
import { useChatStore } from "@/lib/store/useChatStore"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu"

export default function ChatHeader() {
  const queryClient = useQueryClient()
  const { data: gf, isLoading: gfLoading } = useQuery({ queryKey: ["girlfriend"], queryFn: getCurrentGirlfriend })
  const { data: billing } = useQuery({ queryKey: ["billingStatus"], queryFn: getBillingStatus, retry: false })
  const { data: gfList } = useQuery({ queryKey: ["girlfriendsList"], queryFn: listGirlfriends, retry: false })

  const setCurrentGirlfriend = useAppStore((s) => s.setCurrentGirlfriend)
  const setGirlfriend = useAppStore((s) => s.setGirlfriend)
  const setGirlfriends = useAppStore((s) => s.setGirlfriends)
  const resetChat = useChatStore((s) => s.reset)

  const plan = billing?.plan ?? "free"
  const planMeta: Record<string, { icon: typeof Heart; label: string; color: string }> = {
    free: { icon: Heart, label: "Free", color: "text-muted-foreground" },
    plus: { icon: Sparkles, label: "Plus", color: "text-primary" },
    premium: { icon: Crown, label: "Premium", color: "text-amber-400" },
  }
  const pm = planMeta[plan] ?? planMeta.free
  const PlanIcon = pm.icon

  const girlfriends = gfList?.girlfriends ?? []
  const hasMultiple = girlfriends.length > 1

  const handleSwitch = async (girlfriendId: string) => {
    if (girlfriendId === gf?.id) return
    try {
      const res = await switchGirlfriend(girlfriendId)
      setGirlfriends(res.girlfriends, res.current_girlfriend_id)
      setCurrentGirlfriend(girlfriendId)
      const selected = res.girlfriends.find((g) => g.id === girlfriendId)
      if (selected) setGirlfriend(selected)
      // Reset chat and refetch for the new girl
      resetChat()
      queryClient.invalidateQueries({ queryKey: ["girlfriend"] })
      queryClient.invalidateQueries({ queryKey: ["chatHistory"] })
      queryClient.invalidateQueries({ queryKey: ["chatState"] })
      queryClient.invalidateQueries({ queryKey: ["girlfriendsList"] })
      queryClient.invalidateQueries({ queryKey: ["gallery"] })
    } catch {
      // silently fail
    }
  }

  if (gfLoading || !gf) {
    return (
      <header className="flex h-16 items-center gap-4 border-b border-white/10 px-4">
        <Skeleton className="h-10 w-10 rounded-full" />
        <Skeleton className="h-6 w-32" />
      </header>
    )
  }

  return (
    <header className="flex h-16 items-center justify-between gap-4 border-b border-white/10 px-4">
      <div className="flex items-center gap-3">
        <AvatarCircle name={gf.display_name} avatarUrl={gf.avatar_url} size="md" />
        <div>
          {hasMultiple ? (
            <DropdownMenu>
              <DropdownMenuTrigger className="flex items-center gap-1.5 rounded-md px-1 py-0.5 font-semibold outline-none transition-colors hover:bg-white/5 hover:text-primary">
                {gf.display_name ?? gf.name}
                <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" className="min-w-[200px]">
                <div className="flex items-center gap-1.5 px-2 py-1.5 text-xs text-muted-foreground">
                  <Users className="h-3 w-3" />
                  Switch girl
                </div>
                <DropdownMenuSeparator />
                {girlfriends.map((g) => (
                  <DropdownMenuItem
                    key={g.id}
                    onClick={() => handleSwitch(g.id)}
                    className="flex items-center gap-2.5 py-2"
                  >
                    <AvatarCircle name={g.display_name ?? g.name} avatarUrl={g.avatar_url} size="sm" />
                    <span className="flex-1 truncate text-sm font-medium">
                      {g.display_name ?? g.name}
                    </span>
                    {g.id === gf.id && <Check className="h-4 w-4 text-primary" />}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <h1 className="font-semibold">{gf.display_name ?? gf.name}</h1>
          )}
          <div className="flex items-center gap-1.5">
            <PlanIcon className={`h-3 w-3 ${pm.color}`} />
            <p className={`text-xs font-medium ${pm.color}`}>{pm.label}</p>
          </div>
        </div>
      </div>
    </header>
  )
}
