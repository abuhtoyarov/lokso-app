/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { Download, MoveLeft, MoveRight } from "lucide-react";
import useSWR from "swr";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { EmptyStateCompact } from "@plane/propel/empty-state";
import { WorklogService } from "@plane/services";
import type { TWorklogExport, TWorklogExportStatus } from "@plane/types";
import { Spinner, Table } from "@plane/ui";
import { cn, renderFormattedDate } from "@plane/utils";

const worklogService = new WorklogService();

/** Shared with `export-button.tsx` so a fresh export can revalidate every mounted page of this cache. */
export const WORKLOG_EXPORTS_SWR_KEY = "WORKSPACE_WORKLOG_EXPORTS";

/** Statuses that are still in flight — while any row has one of these, the list polls for updates. */
const PENDING_STATUSES = new Set<TWorklogExportStatus>(["queued", "processing"]);

/** How often to poll while an export is queued or processing. */
const POLL_INTERVAL_MS = 4000;

const STATUS_BADGE_CLASSNAME: Record<TWorklogExportStatus, string> = {
  queued: "bg-layer-transparent-hover text-secondary",
  processing: "bg-yellow-500/20 text-yellow-500",
  completed: "bg-success-subtle text-success-primary",
  failed: "bg-danger-subtle text-danger-primary",
};

type Props = {
  workspaceSlug: string;
};

export const WorklogExportHistory = observer(function WorklogExportHistory(props: Props) {
  const { workspaceSlug } = props;
  // translation
  const { t } = useTranslation();
  // state
  const [cursor, setCursor] = useState<string | undefined>(undefined);

  const { data: history, isLoading } = useSWR(
    workspaceSlug ? [WORKLOG_EXPORTS_SWR_KEY, workspaceSlug, cursor] : null,
    workspaceSlug ? () => worklogService.exportHistory(workspaceSlug, cursor) : null,
    {
      // Poll only while something is still queued/processing; SWR itself stops calling the
      // fetcher the moment `refreshInterval` evaluates to 0, so nothing is left running once
      // every row has resolved, and the timer is torn down for free on unmount.
      refreshInterval: (latestData) =>
        latestData?.results?.some((row) => PENDING_STATUSES.has(row.status)) ? POLL_INTERVAL_MS : 0,
    }
  );

  const rows = history?.results ?? [];

  const columns = [
    {
      key: "date",
      content: t("date"),
      tdRender: (row: TWorklogExport) => <span>{renderFormattedDate(row.created_at)}</span>,
    },
    {
      key: "requested_by",
      content: t("common.created_by"),
      tdRender: (row: TWorklogExport) => <span>{row.initiated_by_detail?.display_name}</span>,
    },
    {
      key: "format",
      content: t("workspace_settings.settings.exports.format"),
      tdRender: (row: TWorklogExport) => (
        <span>{t(row.provider === "csv" ? "exporter.csv.title" : "exporter.excel.title")}</span>
      ),
    },
    {
      key: "status",
      content: "",
      tdRender: (row: TWorklogExport) => (
        <div className="flex flex-col items-start gap-1">
          <span className={cn("rounded-sm px-2 py-0.5 text-11", STATUS_BADGE_CLASSNAME[row.status])}>
            {t(`workspace_settings.settings.worklogs.export_status.${row.status}`)}
          </span>
          {row.status === "failed" && (
            <span className="text-11 text-danger-primary">
              {t("workspace_settings.settings.exports.modal.toasts.error.message")}
            </span>
          )}
        </div>
      ),
    },
    {
      key: "download",
      content: t("workspace_settings.settings.worklogs.download"),
      tdRender: (row: TWorklogExport) =>
        row.status === "completed" && row.url ? (
          <a href={row.url} target="_blank" rel="noopener noreferrer">
            <Button variant="tertiary" size="sm" prependIcon={<Download />}>
              {t("workspace_settings.settings.worklogs.download")}
            </Button>
          </a>
        ) : null,
    },
  ];

  return (
    <div className="flex flex-col gap-y-3">
      <h3 className="text-h6-medium text-primary">{t("workspace_settings.settings.worklogs.previous_downloads")}</h3>
      {isLoading ? (
        <div className="flex w-full items-center justify-center py-10">
          <Spinner className="size-5" />
        </div>
      ) : rows.length > 0 ? (
        <div className="flex flex-col gap-y-3">
          <Table
            columns={columns}
            data={rows}
            keyExtractor={(row) => row.id}
            tHeadClassName="border-b border-subtle"
            thClassName="text-left font-medium divide-x-0 text-placeholder"
            tBodyClassName="divide-y-0"
            tBodyTrClassName="divide-x-0 p-4 h-[40px] text-secondary"
            tHeadTrClassName="divide-x-0"
          />
          {(history?.prev_page_results || history?.next_page_results) && (
            <div className="flex items-center justify-end gap-2 text-11">
              <Button
                variant="secondary"
                size="sm"
                disabled={!history?.prev_page_results}
                onClick={() => history?.prev_page_results && setCursor(history.prev_cursor)}
                prependIcon={<MoveLeft />}
              >
                {t("prev")}
              </Button>
              <Button
                variant="secondary"
                size="sm"
                disabled={!history?.next_page_results}
                onClick={() => history?.next_page_results && setCursor(history.next_cursor)}
                appendIcon={<MoveRight />}
              >
                {t("next")}
              </Button>
            </div>
          )}
        </div>
      ) : (
        <EmptyStateCompact
          assetKey="export"
          title={t("settings_empty_state.exports.title")}
          description={t("settings_empty_state.exports.description")}
          align="start"
          rootClassName="py-10"
        />
      )}
    </div>
  );
});
