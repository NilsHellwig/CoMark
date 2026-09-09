"use client";

import Link from "next/link";
import { useState } from "react";
import { resetForgotPassword } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { TextField } from "@/components/ui/text-field";

export default function ForgotPasswordPage() {
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    const form = new FormData(e.currentTarget);
    await resetForgotPassword({ body: { email: String(form.get("email")) } });
    setBusy(false);
    setSent(true);
  }

  return (
    <div>
      <h1 className="text-xl font-semibold tracking-tight text-ink">Reset password</h1>
      {sent ? (
        <p className="mt-3 text-[13px] leading-6 text-ink-soft">
          If an account exists for that address, a reset link is on its way. In
          development the token is printed to the backend logs.
        </p>
      ) : (
        <>
          <p className="mt-1 text-[13px] text-ink-faint">
            We&rsquo;ll email you a link to set a new one.
          </p>
          <form onSubmit={onSubmit} className="mt-6 flex flex-col gap-4">
            <TextField name="email" type="email" label="Email" required autoFocus />
            <Button type="submit" disabled={busy} className="mt-1 w-full">
              {busy ? "Sending…" : "Send reset link"}
            </Button>
          </form>
        </>
      )}
      <p className="mt-6 text-center text-[13px]">
        <Link href="/login" className="text-ink-faint hover:text-ink-soft">
          &larr; Back to sign in
        </Link>
      </p>
    </div>
  );
}
