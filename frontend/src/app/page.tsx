import Link from "next/link";
import { Logo } from "@/components/layout/logo";

export default function LandingPage() {
  return (
    <div className="mx-auto flex min-h-full max-w-3xl flex-col px-6">
      <header className="flex h-16 items-center justify-between">
        <Logo />
        <nav className="flex items-center gap-5 text-[13px] text-ink-soft">
          <Link href="/login" className="hover:text-ink">
            Sign in
          </Link>
          <Link
            href="/register"
            className="rounded-sm bg-ink px-3 py-1.5 font-medium text-paper hover:opacity-90"
          >
            Get started
          </Link>
        </nav>
      </header>

      <main className="flex flex-1 flex-col justify-center py-24">
        <p className="text-[13px] font-medium uppercase tracking-[0.18em] text-ink-faint">
          Collaborative Markdown
        </p>
        <h1 className="mt-4 max-w-xl text-4xl font-semibold leading-[1.15] tracking-tight text-ink">
          Write together, in the same document, at the same time.
        </h1>
        <p className="mt-5 max-w-md text-[15px] leading-7 text-ink-soft">
          Edits sync instantly. You can see where everyone&rsquo;s cursor and pointer are.
          Share a link with anyone &mdash; account or not &mdash; or invite collaborators
          by email.
        </p>
        <div className="mt-8 flex items-center gap-3">
          <Link
            href="/register"
            className="rounded-sm bg-accent px-4 py-2.5 text-sm font-medium text-accent-ink hover:opacity-90"
          >
            Start a document
          </Link>
          <Link
            href="/login"
            className="rounded-sm border border-line-strong px-4 py-2.5 text-sm font-medium text-ink hover:bg-surface-sunken"
          >
            Sign in
          </Link>
        </div>
      </main>

      <footer className="border-t border-line py-6 text-[12px] text-ink-faint">
        A minimal, self-hostable collaborative editor.
      </footer>
    </div>
  );
}
