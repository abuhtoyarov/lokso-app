/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import type { TWorklogJournalRow } from "@plane/types";
import { Table } from "@plane/ui";
import { formatWorklogDuration, renderFormattedDate } from "@plane/utils";

type Props = {
  rows: TWorklogJournalRow[];
};

export const WorklogJournalTable = observer(function WorklogJournalTable(props: Props) {
  const { rows } = props;
  // translation
  const { t } = useTranslation();

  const columns = [
    {
      key: "project",
      content: t("workspace_settings.settings.worklogs.table.project"),
      tdRender: (row: TWorklogJournalRow) => <span>{row.project_name}</span>,
    },
    {
      key: "issue",
      content: t("workspace_settings.settings.worklogs.table.issue"),
      tdRender: (row: TWorklogJournalRow) => (
        <div className="flex flex-col whitespace-normal">
          <span className="text-11 text-tertiary">{row.issue_identifier}</span>
          <span>{row.issue_name}</span>
        </div>
      ),
    },
    {
      key: "logged",
      content: t("workspace_settings.settings.worklogs.table.logged"),
      tdRender: (row: TWorklogJournalRow) => (
        <span>
          {t("workspace_settings.settings.worklogs.table.logged_by_on", {
            name: row.logged_by_display_name,
            date: renderFormattedDate(row.logged_at),
          })}
        </span>
      ),
    },
    {
      key: "time",
      content: t("workspace_settings.settings.worklogs.table.time"),
      tdRender: (row: TWorklogJournalRow) => <span>{formatWorklogDuration(row.duration)}</span>,
    },
  ];

  return (
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
  );
});
