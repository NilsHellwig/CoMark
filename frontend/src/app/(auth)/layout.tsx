import Link from "next/link";
import { Logo } from "@/components/layout/logo";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto flex min-h-full max-w-sm flex-col px-6">
      <header className="flex h-16 items-center">
        <Logo />
      </header>
      <main className="flex flex-1 flex-col justify-center pb-24">{children}</main>
      <footer className="py-6 text-center text-[12px] text-ink-faint">
        <Link href="/" className="hover:text-ink-soft">
          &larr; Back home
        </Link>
      </footer>
    </div>
  );
}
