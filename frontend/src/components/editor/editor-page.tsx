"use client";

import Link from "next/link";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import {
  getDocumentBySlugOptions,
  getDocumentContentOptions,
  updateDocumentMutation,
  whoamiOptions,
} from "@/lib/api";
import { colorFor } from "@/lib/colors";
import { ConnectionDot } from "@/components/editor/connection-dot";
import { MarkdownEditor } from "@/components/editor/markdown-editor";
import { useCollabDoc, type Identity } from "@/components/editor/use-collab-doc";
import { useMarkdownSync } from "@/components/editor/use-markdown-sync";
import { AvatarStack } from "@/components/presence/avatar-stack";
import { usePeers } from "@/components/presence/use-awareness";
import { ShareDialog } from "@/components/share/share-dialog";
import { Button } from "@/components/ui/button";
import { Logo } from "@/components/layout/logo";
import { Spinner } from "@/components/ui/spinner";

export function EditorPage({ slug }: { slug: string }) {
  const docQuery = useQuery({
    ...getDocumentBySlugOptions({ path: { slug } }),
    retry: false,
  });
  const meQuery = useQuery({ ...whoamiOptions(), retry: false });

  if (docQuery.isError) return <AccessDenied />;

  const doc = docQuery.data;
  const me = meQuery.data;
  if (!doc || !me) return <FullPageSpinner />;

  const identity: Identity = {
    id: me.id ?? "anon",
    name: me.display_name ?? "Anonymous",
    color: me.color ?? colorFor(me.id ?? "anon"),
  };

  return (
    <Workspace
      documentId={doc.id}
      title={doc.title}
      canEdit={doc.access_level === "editor" || doc.access_level === "owner"}
      canManage={doc.access_level === "owner"}
      identity={identity}
    />
  );
}

function Workspace({
  documentId,
  title,
  canEdit,
  canManage,
  identity,
}: {
  documentId: string;
  title: string;
  canEdit: boolean;
  canManage: boolean;
  identity: Identity;
}) {
  const { text, provider, status, synced } = useCollabDoc(documentId, identity);
  const contentQuery = useQuery(
    getDocumentContentOptions({ path: { document_id: documentId } }),
  );
  const pushMarkdown = useMarkdownSync(documentId, canEdit);
  const peers = usePeers(provider);

  const [shareOpen, setShareOpen] = useState(false);
  const [serif, setSerif] = useState(false);
  const [docTitle, setDocTitle] = useState(title);

  const rename = useMutation(updateDocumentMutation());
  const initialMarkdown = useMemo(
    () => contentQuery.data?.markdown ?? "",
    [contentQuery.data],
  );

  const ready = provider && !contentQuery.isPending;

  return (
    <div className="flex h-screen flex-col">
      <header className="z-30 shrink-0 border-b border-line bg-paper">
        <div className="flex h-14 items-center gap-4 px-5">
          <Logo href="/dashboard" className="shrink-0" />
          <div className="mx-1 h-4 w-px bg-line" />
          {canManage ? (
            <input
              value={docTitle}
              onChange={(e) => setDocTitle(e.target.value)}
              onBlur={() => {
                if (docTitle.trim() && docTitle !== title) {
                  rename.mutate({
                    path: { document_id: documentId },
                    body: { title: docTitle.trim() },
                  });
                }
              }}
              className="min-w-0 flex-1 bg-transparent text-[15px] font-medium text-ink outline-none"
            />
          ) : (
            <span className="min-w-0 flex-1 truncate text-[15px] font-medium text-ink">
              {docTitle}
            </span>
          )}
          <div className="flex shrink-0 items-center gap-4">
            {provider ? <AvatarStack peers={peers} self={identity} /> : null}
            <ConnectionDot status={status} />
            <button
              onClick={() => setSerif((s) => !s)}
              className="text-[12px] text-ink-faint hover:text-ink"
              title="Toggle preview typeface"
            >
              {serif ? "Sans" : "Serif"}
            </button>
            {canManage ? (
              <Button size="sm" onClick={() => setShareOpen(true)}>
                Share
              </Button>
            ) : null}
          </div>
        </div>
      </header>

      <main className="min-h-0 flex-1">
        {ready ? (
          <MarkdownEditor
            text={text}
            provider={provider}
            editable={canEdit}
            serif={serif}
            synced={synced}
            initialMarkdown={initialMarkdown}
            onMarkdownChange={pushMarkdown}
          />
        ) : (
          <div className="flex h-full items-center justify-center text-ink-faint">
            <Spinner />
          </div>
        )}
      </main>

      {canManage ? (
        <ShareDialog
          open={shareOpen}
          onClose={() => setShareOpen(false)}
          documentId={documentId}
        />
      ) : null}
    </div>
  );
}

function FullPageSpinner() {
  return (
    <div className="grid min-h-screen place-items-center text-ink-faint">
      <Spinner />
    </div>
  );
}

function AccessDenied() {
  return (
    <div className="mx-auto grid min-h-screen max-w-md place-items-center px-6 text-center">
      <div>
        <h1 className="text-lg font-semibold text-ink">No access to this document</h1>
        <p className="mt-2 text-[13px] text-ink-faint">
          The link may have been revoked, or you need to sign in with an invited account.
        </p>
        <Link
          href="/dashboard"
          className="mt-4 inline-block text-[13px] font-medium text-accent hover:underline"
        >
          Go to your documents
        </Link>
      </div>
    </div>
  );
}
