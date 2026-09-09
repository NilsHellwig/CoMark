"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { authCookieLogin, errorMessage, failed, registerRegister } from "@/lib/api";
import { GoogleButton } from "@/components/auth/google-button";
import { Button } from "@/components/ui/button";
import { TextField } from "@/components/ui/text-field";

export default function RegisterPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const form = new FormData(e.currentTarget);
    const email = String(form.get("email"));
    const password = String(form.get("password"));
    const displayName = String(form.get("display_name") || "").trim();

    const created = await registerRegister({
      body: { email, password, display_name: displayName || null },
    });
    if (failed(created)) {
      setError(errorMessage(created, "Could not create the account"));
      setBusy(false);
      return;
    }
    await authCookieLogin({ body: { username: email, password } });
    router.replace("/dashboard");
    router.refresh();
  }

  return (
    <div>
      <h1 className="text-xl font-semibold tracking-tight text-ink">Create an account</h1>
      <p className="mt-1 text-[13px] text-ink-faint">Free, and takes a few seconds.</p>

      <form onSubmit={onSubmit} className="mt-6 flex flex-col gap-4">
        <TextField
          name="display_name"
          label="Name"
          autoComplete="name"
          placeholder="Optional"
        />
        <TextField
          name="email"
          type="email"
          label="Email"
          autoComplete="email"
          required
        />
        <TextField
          name="password"
          type="password"
          label="Password"
          autoComplete="new-password"
          minLength={8}
          required
          error={error}
          hint="At least 8 characters."
        />
        <Button type="submit" disabled={busy} className="mt-1 w-full">
          {busy ? "Creating…" : "Create account"}
        </Button>
      </form>

      <div className="my-5 flex items-center gap-3 text-[11px] uppercase tracking-widest text-ink-faint">
        <span className="h-px flex-1 bg-line" />
        or
        <span className="h-px flex-1 bg-line" />
      </div>
      <GoogleButton label="Sign up with Google" />

      <p className="mt-6 text-center text-[13px] text-ink-faint">
        Already have an account?{" "}
        <Link href="/login" className="font-medium text-ink hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  );
}
