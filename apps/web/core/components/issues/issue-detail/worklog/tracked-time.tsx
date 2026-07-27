/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useState } from "react";
import { observer } from "mobx-react";
import { Plus } from "lucide-react";
import { EUserPermissions } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { WorklogService } from "@plane/services";
import type { TWorklog } from "@plane/types";
import { formatWorklogDuration } from "@plane/utils";
// hooks
import { useUser, useUserPermissions } from "@/hooks/store/user";
// components
import { WorklogEntryList } from "./entry-list";
import { WorklogLogWorkForm } from "./log-work-form";

const worklogService = new WorklogService();

type TIssueWorklogProps = {
  workspaceSlug: string;
  projectId: string;
  issueId: string;
  disabled: boolean;
};

export const IssueWorklog = observer(function IssueWorklog(props: TIssueWorklogProps) {
  const { workspaceSlug, projectId, issueId, disabled } = props;
  const { t } = useTranslation();
  // hooks
  const { data: currentUser } = useUser();
  const { getProjectRoleByWorkspaceSlugAndProjectId } = useUserPermissions();
  const projectRole = getProjectRoleByWorkspaceSlugAndProjectId(workspaceSlug, projectId);
  const isProjectAdmin = projectRole === EUserPermissions.ADMIN;
  // state
  const [worklogs, setWorklogs] = useState<TWorklog[]>([]);
  const [isFormOpen, setIsFormOpen] = useState(false);

  useEffect(() => {
    let isMounted = true;
    worklogService
      .list(workspaceSlug, projectId, issueId)
      .then((response) => {
        if (isMounted) setWorklogs(response ?? []);
        return undefined;
      })
      .catch(() => {
        if (isMounted) setWorklogs([]);
      });
    return () => {
      isMounted = false;
    };
  }, [workspaceSlug, projectId, issueId]);

  const totalDuration = worklogs.reduce((sum, entry) => sum + entry.duration, 0);

  const showErrorToast = () =>
    setToast({
      title: t("toast.error"),
      type: TOAST_TYPE.ERROR,
      message: t("something_went_wrong_please_try_again"),
    });

  const handleCreate = async (data: Pick<TWorklog, "duration" | "description" | "logged_at">) => {
    try {
      const created = await worklogService.create(workspaceSlug, projectId, issueId, data);
      setWorklogs((prev) => [...prev, created]);
      setIsFormOpen(false);
    } catch (_error) {
      showErrorToast();
    }
  };

  const handleUpdate = async (entry: TWorklog, data: Pick<TWorklog, "duration" | "description" | "logged_at">) => {
    try {
      const updated = await worklogService.update(workspaceSlug, projectId, issueId, entry.id, data);
      setWorklogs((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
    } catch (_error) {
      showErrorToast();
    }
  };

  const handleDelete = async (entry: TWorklog) => {
    try {
      await worklogService.remove(workspaceSlug, projectId, issueId, entry.id);
      setWorklogs((prev) => prev.filter((item) => item.id !== entry.id));
    } catch (_error) {
      showErrorToast();
    }
  };

  return (
    <div className="flex w-full flex-col gap-2">
      <div className="flex w-full items-center justify-between gap-2">
        <span className="text-body-xs-regular">{formatWorklogDuration(totalDuration)}</span>
        {!disabled && !isFormOpen && (
          <button
            type="button"
            onClick={() => setIsFormOpen(true)}
            className="flex items-center gap-1 rounded-sm px-1.5 py-0.5 text-body-xs-regular text-tertiary hover:bg-surface-2 hover:text-primary"
          >
            <Plus className="size-3.5" />
            {t("worklog.log_work")}
          </button>
        )}
      </div>

      {isFormOpen && <WorklogLogWorkForm onCancel={() => setIsFormOpen(false)} onSubmit={handleCreate} />}

      <WorklogEntryList
        entries={worklogs}
        currentUserId={currentUser?.id}
        isProjectAdmin={isProjectAdmin}
        disabled={disabled}
        onUpdate={handleUpdate}
        onDelete={handleDelete}
      />
    </div>
  );
});
