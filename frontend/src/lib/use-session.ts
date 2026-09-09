"use client";

import { useQuery } from "@tanstack/react-query";
import { usersCurrentUserOptions, type UserRead } from "@/lib/api";

export type SessionState = {
  user: UserRead | null;
  loading: boolean;
};

export function useSession(): SessionState {
  const { data, isLoading, isError } = useQuery({
    ...usersCurrentUserOptions(),
    retry: false,
    staleTime: 60_000,
  });
  return { user: isError ? null : (data ?? null), loading: isLoading };
}
