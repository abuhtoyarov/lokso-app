/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { Pencil, Trash2 } from "lucide-react";
import { useTranslation } from "@plane/i18n";
import type { TWorklog } from "@plane/types";
import { formatWorklogDuration } from "@plane/utils";
// hooks
import { useMember } from "@/hooks/store/use-member";
// components
import { WorklogLogWorkForm } from "./log-work-form";

type TWorklogEntryListProps = {
  entries: TWorklog[];
  currentUserId: string | undefined;
  isProjectAdmin: boolean;
  disabled: boolean;
  onUpdate: (entry: TWorklog, data: Pick<TWorklog, "duration" | "description" | "logged_at">) => Promise<void>;
  onDelete: (entry: TWorklog) => Promise<void>;
};

export const WorklogEntryList = observer(function WorklogEntryList(props: TWorklogEntryListProps) {
  const { entries, currentUserId, isProjectAdmin, disabled, onUpdate, onDelete } = props;
  const { t } = useTranslation();
  const { getUserDetails } = useMember();
  const [editingEntryId, setEditingEntryId] = useState<string | null>(null);

  if (entries.length === 0) return null;

  return (
    <div className="flex w-full flex-col gap-1.5">
      {entries.map((entry) => {
        const canEditEntry = !disabled && (entry.logged_by === currentUserId || isProjectAdmin);
        const loggedByDetails = getUserDetails(entry.logged_by);

        if (editingEntryId === entry.id) {
          return (
            <WorklogLogWorkForm
              key={entry.id}
              entry={entry}
              onCancel={() => setEditingEntryId(null)}
              onSubmit={async (data) => {
                await onUpdate(entry, data);
                setEditingEntryId(null);
              }}
            />
          );
        }

        return (
          <div
            key={entry.id}
            className="flex items-start justify-between gap-2 rounded-md px-1 py-1 hover:bg-surface-2"
          >
            <div className="flex min-w-0 grow flex-col gap-0.5 text-body-xs-regular">
              <div className="flex flex-wrap items-center gap-1.5 text-secondary">
                <span className="font-medium">{loggedByDetails?.display_name}</span>
                <span className="text-tertiary">{entry.logged_at}</span>
                <span className="text-tertiary">{formatWorklogDuration(entry.duration)}</span>
              </div>
              {entry.description && <span className="truncate text-tertiary">{entry.description}</span>}
            </div>
            {canEditEntry && (
              <div className="flex shrink-0 items-center gap-1">
                <button
                  type="button"
                  title={t("worklog.edit_entry")}
                  aria-label={t("worklog.edit_entry")}
                  onClick={() => setEditingEntryId(entry.id)}
                  className="hover:bg-surface-3 grid place-items-center rounded-sm p-1 text-tertiary hover:text-primary"
                >
                  <Pencil className="size-3.5" />
                </button>
                <button
                  type="button"
                  title={t("worklog.delete_entry")}
                  aria-label={t("worklog.delete_entry")}
                  onClick={() => onDelete(entry)}
                  className="hover:bg-surface-3 grid place-items-center rounded-sm p-1 text-tertiary hover:text-danger-primary"
                >
                  <Trash2 className="size-3.5" />
                </button>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
});
