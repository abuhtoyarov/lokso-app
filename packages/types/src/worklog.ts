/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/** A single time entry as returned by the issue-scoped endpoint. Relations are ids. */
export type TWorklog = {
  id: string;
  issue: string;
  project: string;
  workspace: string;
  logged_by: string;
  /** Whole minutes. Hours are a presentation concern only. */
  duration: number;
  description: string;
  /** Date the work was performed, YYYY-MM-DD. May be in the past. */
  logged_at: string;
  created_at: string;
  updated_at: string;
};

/** A journal row. Same entry, plus the names the table renders. */
export type TWorklogJournalRow = Pick<
  TWorklog,
  "id" | "project" | "issue" | "logged_by" | "duration" | "description" | "logged_at"
> & {
  project_name: string;
  /** Human-facing work item key, e.g. "PROJ-123". */
  issue_identifier: string;
  issue_name: string;
  logged_by_display_name: string;
};

export type TWorklogSummary = {
  /** Whole minutes across everything matching the current filters. */
  total_duration: number;
  entry_count: number;
};

export type TWorklogFilters = {
  users?: string[];
  projects?: string[];
  /** YYYY-MM-DD */
  start_date?: string;
  /** YYYY-MM-DD */
  end_date?: string;
};

export type TWorklogExportProvider = "csv" | "xlsx" | "json";

export type TWorklogExportStatus = "queued" | "processing" | "completed" | "failed";

/** Minimal user shape embedded by `UserLiteSerializer`, as returned on `initiated_by_detail`. */
export type TWorklogExportInitiator = {
  id: string;
  first_name: string;
  last_name: string;
  avatar: string;
  avatar_url: string;
  is_bot: boolean;
  display_name: string;
};

/**
 * A row of `ExporterHistory`, as serialized by `ExporterHistorySerializer` for
 * `type="issue_worklogs"`.
 *
 * Note: the model also has a `filters` column that the serializer still omits,
 * so a past export's original filters are not recoverable from this endpoint.
 */
export type TWorklogExport = {
  id: string;
  provider: TWorklogExportProvider;
  status: TWorklogExportStatus;
  /** Empty unless the export failed — carries the exception text from the task. */
  reason: string;
  /** Present only once status is "completed". */
  url: string | null;
  initiated_by: string;
  initiated_by_detail: TWorklogExportInitiator;
  created_at: string;
  updated_at: string;
};

/** The cursor-paginator envelope. `count` is the page size — `total_count` is the real total. */
export type TWorklogPaginated<T> = {
  count: number;
  total_count: number;
  total_results: number;
  total_pages: number;
  next_cursor: string;
  prev_cursor: string;
  next_page_results: boolean;
  prev_page_results: boolean;
  results: T[];
};
