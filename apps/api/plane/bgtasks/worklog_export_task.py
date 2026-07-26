# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
from uuid import UUID

# Third Party imports
from celery import shared_task

# Module imports
from plane.app.serializers import WorklogExportSerializer
from plane.bgtasks.export_task import create_zip_file, upload_to_s3
from plane.db.models import ExporterHistory, Worklog
from plane.utils.exception_logger import log_exception
from plane.utils.porters.exporter import DataExporter


def worklog_queryset(workspace_id, filters):
    """Every row matching the filters — never a single page.

    Applies the same three base rules as the workspace worklog journal
    (``WorkspaceWorklogEndpoint._filtered_queryset`` in
    ``plane.app.views.worklog.base``): scoped to the workspace, only projects
    with time tracking enabled, and only non-archived projects. Keep these in
    sync with the journal's queryset — they must always agree, since the
    export is a download of the same data the journal shows.

    ``filters["users"]`` / ``filters["projects"]``, if present, are already a
    list of validated UUID strings by the time they reach here —
    ``WorklogExportEndpoint.post`` normalises and validates both the
    comma-separated-string and JSON-list shapes via
    ``_normalize_uuid_list`` before ever creating the ``ExporterHistory`` row,
    so this never has to guess at (or choke on) the raw client input.
    ``filters["start_date"]`` / ``filters["end_date"]``, if present, are
    ISO ``YYYY-MM-DD`` strings already validated via ``_parse_date_param``.
    """
    queryset = Worklog.objects.filter(
        workspace_id=workspace_id,
        project__is_time_tracking_enabled=True,
        project__archived_at__isnull=True,
    ).select_related("project", "issue", "logged_by")

    if filters.get("users"):
        queryset = queryset.filter(logged_by_id__in=filters["users"])
    if filters.get("projects"):
        queryset = queryset.filter(project_id__in=filters["projects"])
    if filters.get("start_date"):
        queryset = queryset.filter(logged_at__gte=filters["start_date"])
    if filters.get("end_date"):
        queryset = queryset.filter(logged_at__lte=filters["end_date"])

    return queryset


@shared_task
def worklog_export_task(provider: str, workspace_id: UUID, token_id: str, slug: str, filters: dict):
    """Export the worklog journal for a workspace.

    provider (str): csv | json | xlsx
    token_id (str): the ExporterHistory token
    filters (dict): users, projects, start_date, end_date
    """
    try:
        exporter_instance = ExporterHistory.objects.get(token=token_id)
        exporter_instance.status = "processing"
        exporter_instance.save(update_fields=["status"])

        worklogs = worklog_queryset(workspace_id, filters or {})

        try:
            exporter = DataExporter(WorklogExportSerializer, format_type=provider)
        except ValueError as e:
            exporter_instance.status = "failed"
            exporter_instance.reason = str(e)
            exporter_instance.save(update_fields=["status", "reason"])
            return

        filename, content = exporter.export(f"{slug}-worklogs", worklogs)
        zip_buffer = create_zip_file([(filename, content)])
        upload_to_s3(zip_buffer, workspace_id, token_id, slug)

    except Exception as e:
        exporter_instance = ExporterHistory.objects.get(token=token_id)
        exporter_instance.status = "failed"
        exporter_instance.reason = str(e)
        exporter_instance.save(update_fields=["status", "reason"])
        log_exception(e)
        return
