export default function Footer() {
  return (
    <footer className="hidden border-t border-white/10 py-4 text-center text-xs text-muted-foreground md:block">
      © {new Date().getFullYear()} Companion. For adults 18+.
    </footer>
  )
}
