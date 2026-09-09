"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { use, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { joinAsGuestMutation, resolveLinkOptions } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Logo } from "@/components/layout/logo";
import { Spinner } from "@/components/ui/spinner";
import { TextField } from "@/components/ui/text-field";

export default function ShareLinkPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = use(params);
  const router = useRouter();
  const [name, setName] = useState("");

  const linkQuery = useQuery({
    ...resolveLinkOptions({ path: { token } }),
    retry: false,
  });

  const join = useMutation({
    ...joinAsGuestMutation(),
    onSuccess: (res) => {
      router.replace(`/d/${res.document_slug}`);
    },
  });

  return (
    <div className="mx-auto flex min-h-full max-w-sm flex-col px-6">
      <header className="flex h-16 items-center">
        <Logo />
      </header>
      <main className="flex flex-1 flex-col justify-center pb-24">
        {linkQuery.isPending ? (
          <div className="flex justify-center text-ink-faint">
            <Spinner />
          </div>
        ) : linkQuery.isError || !linkQuery.data ? (
          <div>
            <h1 className="text-lg font-semibold text-ink">This link is not valid</h1>
            <p className="mt-2 text-[13px] text-ink-faint">
              It may have been revoked or expired. Ask the owner for a new one.
            </p>
          </div>
        ) : (
          <div>
            <p className="text-[13px] text-ink-faint">You&rsquo;ve been invited to</p>
            <h1 className="mt-1 text-xl font-semibold tracking-tight text-ink">
              {linkQuery.data.document.title || "Untitled"}
            </h1>
            <p className="mt-1 text-[13px] text-ink-faint">
              You&rsquo;ll join as a guest with{" "}
              {linkQuery.data.role === "editor" ? "edit" : "view"} access.
            </p>

            <form
              className="mt-6 flex flex-col gap-3"
              onSubmit={(e) => {
                e.preventDefault();
                if (name.trim()) {
                  join.mutate({ path: { token }, body: { display_name: name.trim() } });
                }
              }}
            >
              <TextField
                label="Your name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="How should others see you?"
                autoFocus
                required
                error={join.isError ? "Could not join — try again" : null}
              />
              <Button type="submit" disabled={join.isPending} className="w-full">
                {join.isPending ? "Joining…" : "Open document"}
              </Button>
            </form>

            <p className="mt-5 text-center text-[12px] text-ink-faint">
              Have an account?{" "}
              <Link href="/login" className="font-medium text-ink hover:underline">
                Sign in
              </Link>
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
