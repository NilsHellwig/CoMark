import { Button } from "@/components/ui/button";

export function GoogleButton({ label = "Continue with Google" }: { label?: string }) {
  if (process.env.NEXT_PUBLIC_GOOGLE_ENABLED !== "true") return null;
  return (
    <a href="/api/v1/auth/google/authorize" className="block">
      <Button variant="outline" size="md" className="w-full" tabIndex={-1}>
        <svg width="15" height="15" viewBox="0 0 24 24" aria-hidden>
          <path
            fill="currentColor"
            d="M12 11v3.2h4.5c-.2 1.2-1.5 3.6-4.5 3.6a5 5 0 010-10c1.6 0 2.6.7 3.2 1.3L17.6 4A8 8 0 1012 20c4.6 0 7.7-3.2 7.7-7.8 0-.5 0-.9-.1-1.2H12z"
          />
        </svg>
        {label}
      </Button>
    </a>
  );
}
