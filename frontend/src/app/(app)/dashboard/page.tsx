"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "motion/react";
import {
  createNewDocumentMutation,
  deleteDocumentMutation,
  listDocumentsOptions,
  listDocumentsQueryKey,
  type DocumentListItem,
} from "@/lib/api";
import { fadeUp, listStagger } from "@/lib/motion";
import { formatRelative } from "@/lib/utils";
import { useToast } from "@/components/ui/toast";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";

export default function DashboardPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const { notify } = useToast();

  const { data: docs, isPending } = useQuery(listDocumentsOptions());

  const create = useMutation({
    ...createNewDocumentMutation(),
    onSuccess: (doc) => router.push(`/d/${doc.slug}`),
    onError: () => notify("Could not create the document", "error"),
  });

  const remove = useMutation({
    ...deleteDocumentMutation(),
    onMutate: async (vars) => {
      await qc.cancelQueries({ queryKey: listDocumentsQueryKey() });
      const prev = qc.getQueryData<DocumentListItem[]>(listDocumentsQueryKey());
      qc.setQueryData<DocumentListItem[]>(listDocumentsQueryKey(), (old) =>
        old?.filter((d) => d.id !== vars.path.document_id),
      );
      return { prev };
    },
    onError: (_e, _v, ctx) => {
      if (ctx?.prev) qc.setQueryData(listDocumentsQueryKey(), ctx.prev);
      notify("Delete failed", "error");
    },
    onSettled: () => qc.invalidateQueries({ queryKey: listDocumentsQueryKey() }),
  });

  function onDelete(doc: DocumentListItem) {
    if (confirm(`Delete “${doc.title}”? This cannot be undone.`)) {
      remove.mutate({ path: { document_id: doc.id } });
    }
  }

  return (
    <div>
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-ink">Documents</h1>
          <p className="mt-1 text-[13px] text-ink-faint">
            Everything you own or collaborate on.
          </p>
        </div>
        <Button
          onClick={() => create.mutate({ body: { title: "Untitled" } })}
          disabled={create.isPending}
        >
          {create.isPending ? <Spinner className="text-accent-ink" /> : "New document"}
        </Button>
      </div>

      <div className="mt-8">
        {isPending ? (
          <div className="flex justify-center py-16 text-ink-faint">
            <Spinner />
          </div>
        ) : !docs || docs.length === 0 ? (
          <div className="rounded-lg border border-dashed border-line-strong py-16 text-center">
            <p className="text-sm text-ink-soft">No documents yet.</p>
            <button
              onClick={() => create.mutate({ body: { title: "Untitled" } })}
              className="mt-2 text-[13px] font-medium text-accent hover:underline"
            >
              Create your first one
            </button>
          </div>
        ) : (
          <motion.ul
            variants={listStagger}
            initial="hidden"
            animate="show"
            className="divide-y divide-line border-y border-line"
          >
            {docs.map((doc) => (
              <motion.li key={doc.id} variants={fadeUp} className="group">
                <div className="flex items-center gap-4 py-3.5">
                  <Link href={`/d/${doc.slug}`} className="min-w-0 flex-1">
                    <span className="block truncate text-[15px] font-medium text-ink group-hover:text-accent">
                      {doc.title || "Untitled"}
                    </span>
                    <span className="mt-0.5 block text-[12px] text-ink-faint">
                      {doc.access_level === "owner"
                        ? "Owned by you"
                        : `Shared · ${doc.access_level}`}
                      {" · "}
                      {formatRelative(doc.updated_at)}
                    </span>
                  </Link>
                  {doc.access_level === "owner" ? (
                    <button
                      onClick={() => onDelete(doc)}
                      className="rounded-sm px-2 py-1 text-[12px] text-ink-faint opacity-0 transition hover:bg-danger/10 hover:text-danger group-hover:opacity-100"
                    >
                      Delete
                    </button>
                  ) : null}
                </div>
              </motion.li>
            ))}
          </motion.ul>
        )}
      </div>
    </div>
  );
}
