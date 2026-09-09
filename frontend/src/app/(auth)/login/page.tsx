"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { authCookieLogin, errorMessage, failed } from "@/lib/api";
import { GoogleButton } from "@/components/auth/google-button";
import { Button } from "@/components/ui/button";
import { TextField } from "@/components/ui/text-field";

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const oauthError = params.get("error");

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const form = new FormData(e.currentTarget);
    const result = await authCookieLogin({
      body: {
        username: String(form.get("email")),
        password: String(form.get("password")),
      },
    });
    if (failed(result)) {
      setError(errorMessage(result, "Wrong email or password"));
      setBusy(false);
      return;
    }
    const next = params.get("next");
    router.replace(next && next.startsWith("/") ? next : "/dashboard");
    router.refresh();
  }

  return (
    <div>
      <h1 className="text-xl font-semibold tracking-tight text-ink">Sign in</h1>
      <p className="mt-1 text-[13px] text-ink-faint">Welcome back to CoMark.</p>

      {oauthError ? (
        <p className="mt-4 rounded-sm border border-danger/30 bg-danger/5 px-3 py-2 text-[12px] text-danger">
          Google sign-in did not complete. Try again or use your email.
        </p>
      ) : null}

      <form onSubmit={onSubmit} className="mt-6 flex flex-col gap-4">
        <TextField
          name="email"
          type="email"
          label="Email"
          autoComplete="email"
          required
          autoFocus
        />
        <TextField
          name="password"
          type="password"
          label="Password"
          autoComplete="current-password"
          required
          error={error}
        />
        <Button type="submit" disabled={busy} className="mt-1 w-full">
          {busy ? "Signing in…" : "Sign in"}
        </Button>
      </form>

      <div className="my-5 flex items-center gap-3 text-[11px] uppercase tracking-widest text-ink-faint">
        <span className="h-px flex-1 bg-line" />
        or
        <span className="h-px flex-1 bg-line" />
      </div>
      <GoogleButton />

      <p className="mt-6 text-center text-[13px] text-ink-faint">
        New here?{" "}
        <Link href="/register" className="font-medium text-ink hover:underline">
          Create an account
        </Link>
      </p>
      <p className="mt-2 text-center text-[12px]">
        <Link href="/forgot-password" className="text-ink-faint hover:text-ink-soft">
          Forgot your password?
        </Link>
      </p>
    </div>
  );
}
