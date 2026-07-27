/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { Download } from "lucide-react";
import { mutate } from "swr";
// plane imports
import { useTranslation } from "@plane/i18n";
import { getButtonStyling } from "@plane/propel/button";
import { setToast, TOAST_TYPE } from "@plane/propel/toast";
import { WorklogService } from "@plane/services";
import type { TWorklogExportProvider, TWorklogFilters } from "@plane/types";
import { CustomMenu } from "@plane/ui";
import { cn } from "@plane/utils";
// local imports
import { WORKLOG_EXPORTS_SWR_KEY } from "./export-history";

const worklogService = new WorklogService();

/** Offered on the journal — `json` exists on the backend but isn't a format admins ask for here. */
const EXPORT_PROVIDERS: { provider: TWorklogExportProvider; i18nTitle: string }[] = [
  { provider: "xlsx", i18nTitle: "exporter.excel.title" },
  { provider: "csv", i18nTitle: "exporter.csv.title" },
];

type Props = {
  workspaceSlug: string;
  /** The journal's current filters — what downloads must match what the admin is looking at. */
  filters: TWorklogFilters;
};

export const WorklogExportButton = observer(function WorklogExportButton(props: Props) {
  const { workspaceSlug, filters } = props;
  // translation
  const { t } = useTranslation();
  // state
  const [isRequesting, setIsRequesting] = useState(false);

  const handleExport = async (provider: TWorklogExportProvider) => {
    setIsRequesting(true);
    try {
      await worklogService.requestExport(workspaceSlug, provider, filters);
      // The response never contains a file — only a confirmation that the export was queued.
      // There's no id to track it by either, so the only thing to do is refresh the history list.
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("workspace_settings.settings.worklogs.download"),
        message: t("workspace_settings.settings.exports.modal.toasts.success.message", {
          entity: t(provider === "csv" ? "exporter.csv.title" : "exporter.excel.title"),
        }),
      });
      void mutate((key: unknown) => Array.isArray(key) && key[0] === WORKLOG_EXPORTS_SWR_KEY);
    } catch (error) {
      const errorData = error as { detail?: string; error?: string } | undefined;
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("error"),
        message:
          errorData?.detail || errorData?.error || t("workspace_settings.settings.exports.modal.toasts.error.message"),
      });
    } finally {
      setIsRequesting(false);
    }
  };

  return (
    <CustomMenu
      // A plain element, not `Button` — `CustomMenu` already renders its own `<button>` around
      // `customButton`, and nesting a real `<button>` inside it breaks click handling.
      customButton={
        <div className={cn(getButtonStyling("secondary", "sm"), "gap-1.5")}>
          <Download className="size-3.5 shrink-0" strokeWidth={2} />
          {t("workspace_settings.settings.worklogs.download")}
        </div>
      }
      placement="bottom-end"
      closeOnSelect
      disabled={isRequesting}
    >
      {EXPORT_PROVIDERS.map(({ provider, i18nTitle }) => (
        <CustomMenu.MenuItem key={provider} onClick={() => void handleExport(provider)}>
          {t(i18nTitle)}
        </CustomMenu.MenuItem>
      ))}
    </CustomMenu>
  );
});
