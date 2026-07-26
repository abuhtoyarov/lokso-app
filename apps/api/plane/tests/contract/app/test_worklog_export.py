# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Contract tests for worklog export."""

from datetime import date
from unittest.mock import patch

import pytest

from plane.db.models import ExporterHistory, Issue, Project, ProjectMember, Worklog
from plane.db.models.project import ROLE


@pytest.fixture
def seeded(db, workspace, create_user):
    project = Project.objects.create(
        name="Enabled", identifier="ENAB", workspace=workspace,
        created_by=create_user, is_time_tracking_enabled=True,
    )
    ProjectMember.objects.create(
        project=project, workspace=workspace, member=create_user, role=ROLE.ADMIN.value, is_active=True
    )
    issue = Issue.objects.create(name="A", project=project, created_by=create_user)
    for day, minutes in ((20, 120), (21, 45), (22, 30)):
        Worklog.objects.create(
            project=project, issue=issue, logged_by=create_user, created_by=create_user,
            duration=minutes, logged_at=date(2026, 7, day),
        )
    return project


@pytest.mark.contract
def test_export_creates_history_row_with_worklog_type(session_client, workspace, seeded):
    with patch("plane.app.views.worklog.base.worklog_export_task.delay") as task:
        response = session_client.post(
            f"/api/workspaces/{workspace.slug}/worklogs/exports/",
            data={"provider": "csv"},
            format="json",
        )
    assert response.status_code == 200
    history = ExporterHistory.objects.get()
    assert history.type == "issue_worklogs"
    assert history.provider == "csv"
    assert task.called


@pytest.mark.contract
def test_export_rejects_unknown_provider(session_client, workspace, seeded):
    response = session_client.post(
        f"/api/workspaces/{workspace.slug}/worklogs/exports/",
        data={"provider": "pdf"},
        format="json",
    )
    assert response.status_code == 400
    assert ExporterHistory.objects.count() == 0


@pytest.mark.contract
def test_export_stores_filters(session_client, workspace, seeded):
    with patch("plane.app.views.worklog.base.worklog_export_task.delay"):
        session_client.post(
            f"/api/workspaces/{workspace.slug}/worklogs/exports/",
            data={"provider": "xlsx", "start_date": "2026-07-21", "end_date": "2026-07-22"},
            format="json",
        )
    history = ExporterHistory.objects.get()
    assert history.filters["start_date"] == "2026-07-21"
    assert history.filters["end_date"] == "2026-07-22"


@pytest.mark.contract
def test_history_lists_only_worklog_exports(session_client, workspace, seeded, create_user):
    ExporterHistory.objects.create(
        workspace=workspace, type="issue_exports", provider="csv", initiated_by=create_user
    )
    with patch("plane.app.views.worklog.base.worklog_export_task.delay"):
        session_client.post(
            f"/api/workspaces/{workspace.slug}/worklogs/exports/",
            data={"provider": "csv"},
            format="json",
        )

    response = session_client.get(f"/api/workspaces/{workspace.slug}/worklogs/exports/")
    assert response.status_code == 200
    # ExporterHistorySerializer does not expose a `type` field (see task-5 report),
    # so the type filtering is verified against the database instead of the
    # response body. The response is only checked for containing exactly the
    # worklog-export row (by id), never the issue-export one.
    result_ids = {row["id"] for row in response.json()["results"]}
    worklog_export_ids = {
        str(pk) for pk in ExporterHistory.objects.filter(type="issue_worklogs").values_list("id", flat=True)
    }
    issue_export_ids = {
        str(pk) for pk in ExporterHistory.objects.filter(type="issue_exports").values_list("id", flat=True)
    }
    assert len(worklog_export_ids) == 1
    assert len(issue_export_ids) == 1
    assert result_ids == worklog_export_ids
    assert result_ids.isdisjoint(issue_export_ids)


@pytest.mark.contract
def test_export_covers_whole_filter_not_one_page(db, workspace, seeded):
    from plane.bgtasks.worklog_export_task import worklog_queryset

    assert worklog_queryset(workspace_id=str(workspace.id), filters={}).count() == 3


@pytest.mark.contract
def test_export_queryset_honours_date_filter(db, workspace, seeded):
    from plane.bgtasks.worklog_export_task import worklog_queryset

    filtered = worklog_queryset(
        workspace_id=str(workspace.id),
        filters={"start_date": "2026-07-21", "end_date": "2026-07-22"},
    )
    assert filtered.count() == 2
