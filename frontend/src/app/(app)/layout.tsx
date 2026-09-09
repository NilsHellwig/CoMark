import { redirect } from "next/navigation";
import { AppHeader } from "@/components/layout/app-header";
import { hasSessionCookie } from "@/lib/session";

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  if (!(await hasSessionCookie())) {
    redirect("/login");
  }
  return (
    <div className="min-h-full">
      <AppHeader />
      <div className="mx-auto max-w-4xl px-6 py-12">{children}</div>
    </div>
  );
}
