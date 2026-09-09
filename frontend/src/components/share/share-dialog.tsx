"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  createLinkMutation,
  inviteMemberMutation,
  listMembersOptions,
  listMembersQueryKey,
  listShareLinksOptions,
  listShareLinksQueryKey,
  removeMemberMutation,
  revokeLinkMutation,
  updateMemberRoleMutation,
  type MemberRole,
} from "@/lib/api";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Spinner } from "@/components/ui/spinner";
import { TextField } from "@/components/ui/text-field";
import { useToast } from "@/components/ui/toast";

type Tab = "links" | "people";

function RoleSelect({
  value,
  onChange,
  disabled,
}: {
  value: MemberRole;
  onChange: (r: MemberRole) => void;
  disabled?: boolean;
}) {
  return (
    <select
      value={value}
      disabled={disabled}
      onChange={(e) => onChange(e.target.value as MemberRole)}
      className="h-8 rounded-sm border border-line-strong bg-surface px-2 text-[13px] text-ink"
    >
      <option value="editor">Can edit</option>
      <option value="viewer">Can view</option>
    </select>
  );
}

export function ShareDialog({
  open,
  onClose,
  documentId,
}: {
  open: boolean;
  onClose: () => void;
  documentId: string;
}) {
  const [tab, setTab] = useState<Tab>("links");
  return (
    <Dialog open={open} onClose={onClose} title="Share document" className="max-w-lg">
      <div className="mb-4 flex gap-1 rounded-md bg-surface-sunken p-1 text-[13px]">
        {(["links", "people"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={cn(
              "flex-1 rounded-sm px-3 py-1.5 font-medium capitalize transition-colors",
              tab === t
                ? "bg-surface text-ink shadow-soft"
                : "text-ink-faint hover:text-ink",
            )}
          >
            {t}
          </button>
        ))}
      </div>
      {tab === "links" ? (
        <LinksPanel documentId={documentId} />
      ) : (
        <PeoplePanel documentId={documentId} />
      )}
    </Dialog>
  );
}

function LinksPanel({ documentId }: { documentId: string }) {
  const qc = useQueryClient();
  const { notify } = useToast();
  const key = listShareLinksQueryKey({ path: { document_id: documentId } });
  const { data: links, isPending } = useQuery(
    listShareLinksOptions({ path: { document_id: documentId } }),
  );
  const [role, setRole] = useState<MemberRole>("editor");

  const invalidate = () => qc.invalidateQueries({ queryKey: key });

  const create = useMutation({
    ...createLinkMutation(),
    onSuccess: invalidate,
    onError: () => notify("Could not create link", "error"),
  });
  const revoke = useMutation({ ...revokeLinkMutation(), onSuccess: invalidate });

  const active = (links ?? []).filter((l) => !l.revoked);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <RoleSelect value={role} onChange={setRole} />
        <Button
          size="sm"
          onClick={() =>
            create.mutate({ path: { document_id: documentId }, body: { role } })
          }
          disabled={create.isPending}
        >
          Create link
        </Button>
      </div>

      {isPending ? (
        <Spinner />
      ) : active.length === 0 ? (
        <p className="text-[13px] text-ink-faint">
          No active links. Anyone with a link can join &mdash; with or without an account.
        </p>
      ) : (
        <ul className="flex flex-col divide-y divide-line border-y border-line">
          {active.map((link) => (
            <li key={link.id} className="flex items-center gap-3 py-2.5">
              <span className="flex-1 truncate text-[12px] text-ink-faint">
                {link.url}
              </span>
              <span className="text-[12px] text-ink-soft">
                {link.role === "editor" ? "edit" : "view"}
              </span>
              <button
                onClick={() => {
                  void navigator.clipboard.writeText(link.url);
                  notify("Link copied");
                }}
                className="text-[12px] font-medium text-accent hover:underline"
              >
                Copy
              </button>
              <button
                onClick={() => revoke.mutate({ path: { link_id: link.id } })}
                className="text-[12px] text-ink-faint hover:text-danger"
              >
                Revoke
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function PeoplePanel({ documentId }: { documentId: string }) {
  const qc = useQueryClient();
  const { notify } = useToast();
  const key = listMembersQueryKey({ path: { document_id: documentId } });
  const { data, isPending } = useQuery(
    listMembersOptions({ path: { document_id: documentId } }),
  );
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<MemberRole>("editor");

  const invalidate = () => qc.invalidateQueries({ queryKey: key });
  const invite = useMutation({
    ...inviteMemberMutation(),
    onSuccess: (res) => {
      invalidate();
      setEmail("");
      notify(res.invitation.accepted_at ? "Added" : "Invitation sent");
    },
    onError: () => notify("Could not invite", "error"),
  });
  const changeRole = useMutation({
    ...updateMemberRoleMutation(),
    onSuccess: invalidate,
  });
  const remove = useMutation({ ...removeMemberMutation(), onSuccess: invalidate });

  return (
    <div className="flex flex-col gap-4">
      <form
        className="flex items-end gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (email)
            invite.mutate({ path: { document_id: documentId }, body: { email, role } });
        }}
      >
        <div className="flex-1">
          <TextField
            type="email"
            placeholder="name@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
        <RoleSelect value={role} onChange={setRole} />
        <Button size="sm" type="submit" disabled={invite.isPending}>
          Invite
        </Button>
      </form>

      {isPending ? (
        <Spinner />
      ) : (
        <ul className="flex flex-col divide-y divide-line border-y border-line">
          {data?.members.map((m, i) => (
            <li key={m.user.id} className="flex items-center gap-3 py-2.5">
              <span className="flex-1 truncate text-[13px] text-ink">
                {m.user.display_name ?? m.user.email}
              </span>
              {i === 0 ? (
                <span className="text-[12px] text-ink-faint">Owner</span>
              ) : (
                <>
                  <RoleSelect
                    value={m.role}
                    onChange={(r) =>
                      changeRole.mutate({
                        path: { document_id: documentId, user_id: m.user.id },
                        body: { role: r },
                      })
                    }
                  />
                  <button
                    onClick={() =>
                      remove.mutate({
                        path: { document_id: documentId, user_id: m.user.id },
                      })
                    }
                    className="text-[12px] text-ink-faint hover:text-danger"
                  >
                    Remove
                  </button>
                </>
              )}
            </li>
          ))}
          {data?.pending_invitations.map((inv) => (
            <li key={inv.id} className="flex items-center gap-3 py-2.5 text-ink-faint">
              <span className="flex-1 truncate text-[13px]">{inv.email}</span>
              <span className="text-[12px]">Pending</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
