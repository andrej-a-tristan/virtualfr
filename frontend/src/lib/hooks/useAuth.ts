import { useEffect } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { getMe, logout as apiLogout } from "@/lib/api/endpoints"
import { useAppStore } from "@/lib/store/useAppStore"

export function useAuth() {
  const queryClient = useQueryClient()
  const { user, setUser, reset } = useAppStore()
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["me"],
    queryFn: getMe,
    retry: false,
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  })
  const logoutMutation = useMutation({
    mutationFn: apiLogout,
    onSuccess: () => {
      reset()
      queryClient.clear()
    },
  })

  // Sync server data to local store (as an effect, not during render)
  useEffect(() => {
    if (data && !user) setUser(data)
  }, [data, user, setUser])

  // Merge: prefer store user for fields that may be updated locally before API refetch
  const mergedUser = data
    ? {
        ...data,
        age_gate_passed: data.age_gate_passed || (user?.age_gate_passed ?? false),
        has_girlfriend: data.has_girlfriend || (user?.has_girlfriend ?? false),
      }
    : user
  return {
    user: mergedUser,
    isLoading,
    isError,
    isAuthenticated: !!data,
    refetch,
    logout: logoutMutation.mutateAsync,
  }
}
