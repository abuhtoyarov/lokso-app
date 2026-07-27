/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import useSWR from "swr";
import { MoveLeft, MoveRight } from "lucide-react";
// plane imports
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { EmptyStateCompact } from "@plane/propel/empty-state";
import { Button } from "@plane/propel/button";
import { WorklogService } from "@plane/services";
import type { TWorklogFilters } from "@plane/types";
import { Spinner } from "@plane/ui";
import { cn, renderFormattedPayloadDate } from "@plane/utils";
// components
import { NotAuthorizedView } from "@/components/auth-screens/not-authorized-view";
import { PageHead } from "@/components/core/page-title";
import { SettingsContentWrapper } from "@/components/settings/content-wrapper";
import { SettingsHeading } from "@/components/settings/heading";
import {
  EMPTY_WORKLOG_JOURNAL_FILTERS,
  WorklogExportButton,
  WorklogExportHistory,
  WorklogJournalFilters,
  WorklogJournalSummary,
  WorklogJournalTable,
  type TWorklogJournalFilters,
} from "@/components/worklogs";
// hooks
import { useWorkspace } from "@/hooks/store/use-workspace";
import { useUserPermissions } from "@/hooks/store/user";
// local imports
import { WorklogsWorkspaceSettingsHeader } from "./header";

const worklogService = new WorklogService();

function WorklogsPage() {
  // store hooks
  const { workspaceUserInfo, allowPermissions } = useUserPermissions();
  const { currentWorkspace } = useWorkspace();
  const { t } = useTranslation();
  // router params
  const { workspaceSlug } = useParams();
  const workspaceSlugStr = workspaceSlug?.toString();

  // state
  const [filters, setFilters] = useState<TWorklogJournalFilters>(EMPTY_WORKLOG_JOURNAL_FILTERS);
  const [cursor, setCursor] = useState<string | undefined>(undefined);

  // derived values
  // Journal is admin-only: the backend returns 403 to anyone else, so the page must not
  // offer more access than that (unlike exports, which also allows MEMBER).
  const canViewWorklogs = allowPermissions([EUserPermissions.ADMIN], EUserPermissionsLevel.WORKSPACE);
  const pageTitle = currentWorkspace?.name
    ? `${currentWorkspace.name} - ${t("workspace_settings.settings.worklogs.title")}`
    : undefined;

  const apiFilters: TWorklogFilters = {
    users: filters.users.length ? filters.users : undefined,
    projects: filters.projects.length ? filters.projects : undefined,
    start_date: renderFormattedPayloadDate(filters.dateRange.from),
    end_date: renderFormattedPayloadDate(filters.dateRange.to),
  };
  const filtersKey = JSON.stringify(apiFilters);

  const { data: journal, isLoading: isJournalLoading } = useSWR(
    workspaceSlugStr && canViewWorklogs ? ["WORKSPACE_WORKLOG_JOURNAL", workspaceSlugStr, filtersKey, cursor] : null,
    workspaceSlugStr ? () => worklogService.journal(workspaceSlugStr, apiFilters, cursor) : null
  );

  const { data: summary } = useSWR(
    workspaceSlugStr && canViewWorklogs ? ["WORKSPACE_WORKLOG_SUMMARY", workspaceSlugStr, filtersKey] : null,
    workspaceSlugStr ? () => worklogService.summary(workspaceSlugStr, apiFilters) : null
  );

  const handleFiltersChange = (next: TWorklogJournalFilters) => {
    setFilters(next);
    // A filter change invalidates the current page — start back at the top.
    setCursor(undefined);
  };

  // if user is not authorized to view this page
  if (workspaceUserInfo && !canViewWorklogs) {
    return <NotAuthorizedView section="settings" className="h-auto" />;
  }

  const rows = journal?.results ?? [];
  // `total_duration`/`entry_count` are always numbers — `0` on an empty result, never null.
  const totalDuration = summary?.total_duration ?? 0;

  return (
    <SettingsContentWrapper header={<WorklogsWorkspaceSettingsHeader />} hugging>
      <PageHead title={pageTitle} />
      <div
        className={cn("flex w-full flex-col gap-y-6", {
          "opacity-60": !canViewWorklogs,
        })}
      >
        <SettingsHeading
          title={t("workspace_settings.settings.worklogs.heading")}
          description={t("workspace_settings.settings.worklogs.description")}
          control={
            canViewWorklogs &&
            workspaceSlugStr && <WorklogExportButton workspaceSlug={workspaceSlugStr} filters={apiFilters} />
          }
        />
        <WorklogJournalFilters filters={filters} onChange={handleFiltersChange} />
        <WorklogJournalSummary totalDuration={totalDuration} />
        {isJournalLoading ? (
          <div className="flex w-full items-center justify-center py-20">
            <Spinner className="size-5" />
          </div>
        ) : rows.length > 0 ? (
          <div className="flex flex-col gap-y-3">
            <WorklogJournalTable rows={rows} />
            {(journal?.prev_page_results || journal?.next_page_results) && (
              <div className="flex items-center justify-end gap-2 text-11">
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={!journal?.prev_page_results}
                  onClick={() => journal?.prev_page_results && setCursor(journal.prev_cursor)}
                  prependIcon={<MoveLeft />}
                >
                  {t("prev")}
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={!journal?.next_page_results}
                  onClick={() => journal?.next_page_results && setCursor(journal.next_cursor)}
                  appendIcon={<MoveRight />}
                >
                  {t("next")}
                </Button>
              </div>
            )}
          </div>
        ) : (
          <EmptyStateCompact
            assetKey="worklog"
            title={t("settings_empty_state.worklogs.title")}
            description={t("settings_empty_state.worklogs.description")}
            align="start"
            rootClassName="py-20"
          />
        )}
        {canViewWorklogs && workspaceSlugStr && <WorklogExportHistory workspaceSlug={workspaceSlugStr} />}
      </div>
    </SettingsContentWrapper>
  );
}

export default observer(WorklogsPage);
