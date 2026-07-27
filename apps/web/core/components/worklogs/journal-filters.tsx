/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import { useTranslation } from "@plane/i18n";
// components
import { DateRangeDropdown } from "@/components/dropdowns/date-range";
import { MemberDropdown } from "@/components/dropdowns/member/dropdown";
import { ProjectDropdown } from "@/components/dropdowns/project/dropdown";

/** The journal filters in UI shape — converted to `TWorklogFilters` (ISO date strings) by the caller. */
export type TWorklogJournalFilters = {
  users: string[];
  projects: string[];
  dateRange: {
    from: Date | undefined;
    to: Date | undefined;
  };
};

export const EMPTY_WORKLOG_JOURNAL_FILTERS: TWorklogJournalFilters = {
  users: [],
  projects: [],
  dateRange: { from: undefined, to: undefined },
};

type Props = {
  filters: TWorklogJournalFilters;
  onChange: (filters: TWorklogJournalFilters) => void;
};

export const WorklogJournalFilters = observer(function WorklogJournalFilters(props: Props) {
  const { filters, onChange } = props;
  // translation
  const { t } = useTranslation();

  return (
    <div className="flex flex-wrap items-center gap-2">
      <MemberDropdown
        multiple
        value={filters.users}
        onChange={(users) => onChange({ ...filters, users })}
        placeholder={t("workspace_settings.settings.worklogs.filters.users")}
        buttonVariant="border-with-text"
      />
      <ProjectDropdown
        multiple
        value={filters.projects}
        onChange={(projects) => onChange({ ...filters, projects })}
        placeholder={t("workspace_settings.settings.worklogs.filters.projects")}
        buttonVariant="border-with-text"
      />
      <DateRangeDropdown
        value={filters.dateRange}
        onSelect={(range) => onChange({ ...filters, dateRange: { from: range?.from, to: range?.to } })}
        buttonVariant="border-with-text"
        isClearable
        placeholder={{
          from: t("workspace_settings.settings.worklogs.filters.start_date"),
          to: t("workspace_settings.settings.worklogs.filters.end_date"),
        }}
      />
    </div>
  );
});
