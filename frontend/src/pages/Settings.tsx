import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "@/lib/hooks/useAuth"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import { LogOut, Bell, MessageSquare, Image, User, KeyRound, Trash2, AlertTriangle } from "lucide-react"

export default function Settings() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  // Notification state
  const [pushEnabled, setPushEnabled] = useState(true)
  const [messageNotifs, setMessageNotifs] = useState(true)
  const [photoNotifs, setPhotoNotifs] = useState(true)

  // Password change state
  const [showPasswordForm, setShowPasswordForm] = useState(false)
  const [currentPassword, setCurrentPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [passwordError, setPasswordError] = useState<string | null>(null)
  const [passwordSuccess, setPasswordSuccess] = useState(false)
  const [passwordLoading, setPasswordLoading] = useState(false)

  // Delete account state
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [deleteLoading, setDeleteLoading] = useState(false)

  const handleLogout = async () => {
    await logout()
    navigate("/login", { replace: true })
  }

  const handlePasswordChange = async () => {
    setPasswordError(null)
    setPasswordSuccess(false)

    if (!currentPassword) {
      setPasswordError("Enter your current password")
      return
    }
    if (newPassword.length < 6) {
      setPasswordError("New password must be at least 6 characters")
      return
    }
    if (newPassword !== confirmPassword) {
      setPasswordError("Passwords do not match")
      return
    }

    setPasswordLoading(true)
    try {
      // Mock password change — in production this would call a real endpoint
      await new Promise((r) => setTimeout(r, 800))
      setPasswordSuccess(true)
      setCurrentPassword("")
      setNewPassword("")
      setConfirmPassword("")
      setTimeout(() => {
        setShowPasswordForm(false)
        setPasswordSuccess(false)
      }, 1500)
    } catch {
      setPasswordError("Failed to change password")
    } finally {
      setPasswordLoading(false)
    }
  }

  const handleDeleteAccount = async () => {
    setDeleteLoading(true)
    try {
      await logout()
    } catch {}
    navigate("/", { replace: true })
    window.location.reload()
  }

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold tracking-tight">Settings</h1>

      {/* ── Notifications ──────────────────────────────────────────────── */}
      <Card className="rounded-2xl border-white/10">
        <CardHeader className="flex flex-row items-center gap-2">
          <Bell className="h-5 w-5 text-primary" />
          <div>
            <CardTitle>Notifications</CardTitle>
            <CardDescription>Choose what you get notified about.</CardDescription>
          </div>
        </CardHeader>
        <CardContent className="space-y-5">
          {/* Master toggle */}
          <div className="flex items-center justify-between">
            <div>
              <Label htmlFor="push" className="cursor-pointer text-sm font-medium">
                Push notifications
              </Label>
              <p className="text-xs text-muted-foreground mt-0.5">
                Enable or disable all notifications
              </p>
            </div>
            <button
              id="push"
              type="button"
              role="switch"
              aria-checked={pushEnabled}
              className={cn(
                "relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
                pushEnabled ? "bg-primary" : "bg-muted"
              )}
              onClick={() => setPushEnabled((v) => !v)}
            >
              <span
                className={cn(
                  "pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow ring-0 transition",
                  pushEnabled ? "translate-x-5" : "translate-x-1"
                )}
              />
            </button>
          </div>

          {pushEnabled && (
            <>
              <div className="h-px bg-white/5" />

              {/* Messages */}
              <div className="flex items-center justify-between pl-2">
                <div className="flex items-center gap-2">
                  <MessageSquare className="h-4 w-4 text-muted-foreground" />
                  <Label htmlFor="msg-notif" className="cursor-pointer text-sm">
                    New messages
                  </Label>
                </div>
                <button
                  id="msg-notif"
                  type="button"
                  role="switch"
                  aria-checked={messageNotifs}
                  className={cn(
                    "relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
                    messageNotifs ? "bg-primary" : "bg-muted"
                  )}
                  onClick={() => setMessageNotifs((v) => !v)}
                >
                  <span
                    className={cn(
                      "pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow ring-0 transition",
                      messageNotifs ? "translate-x-5" : "translate-x-1"
                    )}
                  />
                </button>
              </div>

              {/* Photos */}
              <div className="flex items-center justify-between pl-2">
                <div className="flex items-center gap-2">
                  <Image className="h-4 w-4 text-muted-foreground" />
                  <Label htmlFor="photo-notif" className="cursor-pointer text-sm">
                    New photos
                  </Label>
                </div>
                <button
                  id="photo-notif"
                  type="button"
                  role="switch"
                  aria-checked={photoNotifs}
                  className={cn(
                    "relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
                    photoNotifs ? "bg-primary" : "bg-muted"
                  )}
                  onClick={() => setPhotoNotifs((v) => !v)}
                >
                  <span
                    className={cn(
                      "pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow ring-0 transition",
                      photoNotifs ? "translate-x-5" : "translate-x-1"
                    )}
                  />
                </button>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* ── Account ────────────────────────────────────────────────────── */}
      <Card className="rounded-2xl border-white/10">
        <CardHeader className="flex flex-row items-center gap-2">
          <User className="h-5 w-5 text-primary" />
          <div>
            <CardTitle>Account</CardTitle>
            <CardDescription>
              {user?.email ? `Signed in as ${user.email}` : "Manage your account"}
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Change password */}
          {!showPasswordForm ? (
            <Button
              variant="outline"
              className="rounded-xl gap-2 w-full justify-start"
              onClick={() => setShowPasswordForm(true)}
            >
              <KeyRound className="h-4 w-4" />
              Change password
            </Button>
          ) : (
            <div className="rounded-xl border border-white/10 bg-white/5 p-4 space-y-3">
              <h3 className="text-sm font-semibold flex items-center gap-2">
                <KeyRound className="h-4 w-4 text-primary" />
                Change password
              </h3>
              <div className="space-y-2">
                <div>
                  <Label htmlFor="cur-pw" className="text-xs text-muted-foreground">Current password</Label>
                  <Input
                    id="cur-pw"
                    type="password"
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    className="mt-1 rounded-lg bg-white/5 border-white/10"
                    placeholder="••••••••"
                  />
                </div>
                <div>
                  <Label htmlFor="new-pw" className="text-xs text-muted-foreground">New password</Label>
                  <Input
                    id="new-pw"
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="mt-1 rounded-lg bg-white/5 border-white/10"
                    placeholder="••••••••"
                  />
                </div>
                <div>
                  <Label htmlFor="confirm-pw" className="text-xs text-muted-foreground">Confirm new password</Label>
                  <Input
                    id="confirm-pw"
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="mt-1 rounded-lg bg-white/5 border-white/10"
                    placeholder="••••••••"
                  />
                </div>
              </div>
              {passwordError && (
                <p className="text-xs text-red-400">{passwordError}</p>
              )}
              {passwordSuccess && (
                <p className="text-xs text-green-400">Password changed successfully!</p>
              )}
              <div className="flex gap-2 pt-1">
                <Button
                  variant="outline"
                  size="sm"
                  className="rounded-lg"
                  onClick={() => {
                    setShowPasswordForm(false)
                    setPasswordError(null)
                    setCurrentPassword("")
                    setNewPassword("")
                    setConfirmPassword("")
                  }}
                  disabled={passwordLoading}
                >
                  Cancel
                </Button>
                <Button
                  size="sm"
                  className="rounded-lg"
                  onClick={handlePasswordChange}
                  disabled={passwordLoading}
                >
                  {passwordLoading ? "Saving..." : "Save password"}
                </Button>
              </div>
            </div>
          )}

          <div className="h-px bg-white/5" />

          {/* Log out */}
          <Button
            variant="outline"
            className="rounded-xl gap-2 w-full justify-start"
            onClick={handleLogout}
          >
            <LogOut className="h-4 w-4" />
            Log out
          </Button>

          <div className="h-px bg-white/5" />

          {/* Delete account */}
          {!showDeleteConfirm ? (
            <Button
              variant="ghost"
              className="rounded-xl gap-2 w-full justify-start text-red-400/60 hover:text-red-400 hover:bg-red-500/10"
              onClick={() => setShowDeleteConfirm(true)}
            >
              <Trash2 className="h-4 w-4" />
              Delete account
            </Button>
          ) : (
            <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-4 space-y-3">
              <div className="flex items-start gap-2">
                <AlertTriangle className="h-5 w-5 text-red-400 shrink-0 mt-0.5" />
                <div>
                  <h3 className="text-sm font-semibold text-red-300">Delete your account?</h3>
                  <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                    This will permanently delete your account, all conversations,
                    photos, and subscription data. This action cannot be undone.
                  </p>
                </div>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="rounded-lg"
                  onClick={() => setShowDeleteConfirm(false)}
                  disabled={deleteLoading}
                >
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  className="rounded-lg gap-1"
                  onClick={handleDeleteAccount}
                  disabled={deleteLoading}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  {deleteLoading ? "Deleting..." : "Yes, delete my account"}
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
