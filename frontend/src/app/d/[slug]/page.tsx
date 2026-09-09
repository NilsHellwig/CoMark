import { redirect } from "next/navigation";
import { EditorPage } from "@/components/editor/editor-page";
import { hasAnyAccessCookie } from "@/lib/session";

export default async function DocumentPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  if (!(await hasAnyAccessCookie())) {
    redirect(`/login?next=${encodeURIComponent(`/d/${slug}`)}`);
  }
  return <EditorPage slug={slug} />;
}
