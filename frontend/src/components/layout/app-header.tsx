"use client";

import { useRouter } from "next/navigation";
import { authCookieLogout } from "@/lib/api";
import { useSession } from "@/lib/use-session";
import { Avatar } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Logo } from "@/components/layout/logo";

export function AppHeader() {
  const { user } = useSession();
  const router = useRouter();

  async function logout() {
    await authCookieLogout();
    router.replace("/login");
    router.refresh();
  }

  return (
    <header className="sticky top-0 z-30 border-b border-line bg-paper/85 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-4xl items-center justify-between px-6">
        <Logo href="/dashboard" />
        <div className="flex items-center gap-3">
          {user ? (
            <>
              <span className="hidden text-[13px] text-ink-faint sm:inline">
                {user.display_name ?? user.email}
              </span>
              <Avatar name={user.display_name ?? user.email} seed={user.id} size={28} />
              <Button variant="ghost" size="sm" onClick={logout}>
                Sign out
              </Button>
            </>
          ) : null}
        </div>
      </div>
    </header>
  );
}
