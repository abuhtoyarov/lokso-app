/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import type {
  TWorklog,
  TWorklogExport,
  TWorklogExportProvider,
  TWorklogFilters,
  TWorklogJournalRow,
  TWorklogPaginated,
  TWorklogSummary,
} from "@plane/types";
import { APIService } from "../api.service";

/** Serialises filters the way both the journal and the export accept them. */
const toQuery = (filters: TWorklogFilters): Record<string, string> => {
  const query: Record<string, string> = {};
  if (filters.users?.length) query.users = filters.users.join(",");
  if (filters.projects?.length) query.projects = filters.projects.join(",");
  if (filters.start_date) query.start_date = filters.start_date;
  if (filters.end_date) query.end_date = filters.end_date;
  return query;
};

/**
 * Service class for managing worklog operations.
 * Covers per-work-item time entries as well as the workspace-wide journal,
 * summary and export flows.
 * @extends {APIService}
 */
export class WorklogService extends APIService {
  /**
   * Creates an instance of WorklogService
   * @param {string} [BASE_URL] - The base URL for API requests
   */
  constructor(BASE_URL?: string) {
    super(BASE_URL || API_BASE_URL);
  }

  /**
   * Time entries on one work item. Returns a bare array — this endpoint is not paginated.
   * @param {string} workspaceSlug - The workspace slug
   * @param {string} projectId - The project id
   * @param {string} issueId - The work item id
   * @returns {Promise<TWorklog[]>} Promise resolving to the work item's worklogs
   * @throws {Error} If the API request fails
   */
  async list(workspaceSlug: string, projectId: string, issueId: string): Promise<TWorklog[]> {
    return this.get(`/api/workspaces/${workspaceSlug}/projects/${projectId}/issues/${issueId}/worklogs/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  /**
   * Logs a new time entry against a work item.
   * @param {string} workspaceSlug - The workspace slug
   * @param {string} projectId - The project id
   * @param {string} issueId - The work item id
   * @param {object} data - The entry's duration, description and logged date
   * @returns {Promise<TWorklog>} Promise resolving to the created worklog
   * @throws {Error} If the API request fails
   */
  async create(
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    data: Pick<TWorklog, "duration" | "description" | "logged_at">
  ): Promise<TWorklog> {
    return this.post(`/api/workspaces/${workspaceSlug}/projects/${projectId}/issues/${issueId}/worklogs/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  /**
   * Updates an existing time entry.
   * @param {string} workspaceSlug - The workspace slug
   * @param {string} projectId - The project id
   * @param {string} issueId - The work item id
   * @param {string} worklogId - The worklog id
   * @param {object} data - The fields to update
   * @returns {Promise<TWorklog>} Promise resolving to the updated worklog
   * @throws {Error} If the API request fails
   */
  async update(
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    worklogId: string,
    data: Partial<Pick<TWorklog, "duration" | "description" | "logged_at">>
  ): Promise<TWorklog> {
    return this.patch(
      `/api/workspaces/${workspaceSlug}/projects/${projectId}/issues/${issueId}/worklogs/${worklogId}/`,
      data
    )
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  /**
   * Deletes a time entry.
   * @param {string} workspaceSlug - The workspace slug
   * @param {string} projectId - The project id
   * @param {string} issueId - The work item id
   * @param {string} worklogId - The worklog id
   * @returns {Promise<void>}
   * @throws {Error} If the API request fails
   */
  async remove(workspaceSlug: string, projectId: string, issueId: string, worklogId: string): Promise<void> {
    return this.delete(
      `/api/workspaces/${workspaceSlug}/projects/${projectId}/issues/${issueId}/worklogs/${worklogId}/`
    )
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  /**
   * Workspace-wide journal. Paginated — read `total_count`, not `count`, for the real total.
   * @param {string} workspaceSlug - The workspace slug
   * @param {TWorklogFilters} [filters] - Filters to narrow the journal
   * @param {string} [cursor] - Pagination cursor
   * @returns {Promise<TWorklogPaginated<TWorklogJournalRow>>} Promise resolving to a page of journal rows
   * @throws {Error} If the API request fails
   */
  async journal(
    workspaceSlug: string,
    filters: TWorklogFilters = {},
    cursor?: string
  ): Promise<TWorklogPaginated<TWorklogJournalRow>> {
    const params: Record<string, string> = { ...toQuery(filters) };
    if (cursor) params.cursor = cursor;
    return this.get(`/api/workspaces/${workspaceSlug}/worklogs/`, { params })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  /**
   * Total logged time for the same filters the journal accepts.
   * @param {string} workspaceSlug - The workspace slug
   * @param {TWorklogFilters} [filters] - Filters to narrow the summary
   * @returns {Promise<TWorklogSummary>} Promise resolving to the aggregate totals
   * @throws {Error} If the API request fails
   */
  async summary(workspaceSlug: string, filters: TWorklogFilters = {}): Promise<TWorklogSummary> {
    return this.get(`/api/workspaces/${workspaceSlug}/worklogs/summary/`, { params: toQuery(filters) })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  /**
   * Queues an export. Resolves immediately — the file is not ready yet. Poll `exportHistory`.
   * @param {string} workspaceSlug - The workspace slug
   * @param {TWorklogExportProvider} provider - The export file format
   * @param {TWorklogFilters} [filters] - Filters to narrow the export
   * @returns {Promise<{ message: string }>} Promise resolving to a confirmation message
   * @throws {Error} If the API request fails
   */
  async requestExport(
    workspaceSlug: string,
    provider: TWorklogExportProvider,
    filters: TWorklogFilters = {}
  ): Promise<{ message: string }> {
    return this.post(`/api/workspaces/${workspaceSlug}/worklogs/exports/`, { provider, ...toQuery(filters) })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  /**
   * Past worklog export requests and their status.
   * @param {string} workspaceSlug - The workspace slug
   * @param {string} [cursor] - Pagination cursor
   * @returns {Promise<TWorklogPaginated<TWorklogExport>>} Promise resolving to a page of export history
   * @throws {Error} If the API request fails
   */
  async exportHistory(workspaceSlug: string, cursor?: string): Promise<TWorklogPaginated<TWorklogExport>> {
    const params: Record<string, string> = {};
    if (cursor) params.cursor = cursor;
    return this.get(`/api/workspaces/${workspaceSlug}/worklogs/exports/`, { params })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}
