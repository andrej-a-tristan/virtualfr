import { useEffect } from "react"
import { Outlet } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { listGirlfriends } from "@/lib/api/endpoints"
import { useAppStore } from "@/lib/store/useAppStore"
import TopNav from "./TopNav"
import SideNav from "./SideNav"
import MobileNav from "./MobileNav"
import Footer from "./Footer"
import StripeProvider from "@/components/billing/StripeProvider"

export default function AppShell() {
  const setGirlfriends = useAppStore((s) => s.setGirlfriends)

  const { data: gfList } = useQuery({
    queryKey: ["girlfriendsList"],
    queryFn: listGirlfriends,
    retry: false,
    staleTime: 10_000,
  })

  // Sync girlfriends list + current id into the zustand store
  useEffect(() => {
    if (gfList?.girlfriends) {
      setGirlfriends(gfList.girlfriends, gfList.current_girlfriend_id)
    }
  }, [gfList, setGirlfriends])

  return (
    <StripeProvider>
      <div className="flex min-h-screen flex-col">
        <TopNav />
        <div className="flex flex-1">
          <SideNav />
          <main className="flex-1 overflow-auto pb-20 md:pb-0 md:pt-0">
            <div className="mx-auto max-w-5xl p-4 md:p-6">
              <Outlet />
            </div>
          </main>
        </div>
        <Footer />
        <MobileNav />
      </div>
    </StripeProvider>
  )
}
