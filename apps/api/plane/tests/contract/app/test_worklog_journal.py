# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Contract tests for the workspace-level worklog journal."""

from datetime import date

import pytest

from plane.db.models import Issue, Project, ProjectMember, WorkspaceMember, Worklog
from plane.db.models.project import ROLE


def _project(workspace, user, name, identifier, enabled=True):
    project = Project.objects.create(
        name=name, identifier=identifier, workspace=workspace,
        created_by=user, is_time_tracking_enabled=enabled,
    )
    ProjectMember.objects.create(
        project=project, workspace=workspace, member=user, role=ROLE.ADMIN.value, is_active=True
    )
    return project


@pytest.fixture
def seeded(db, workspace, create_user):
    enabled = _project(workspace, create_user, "Enabled", "ENAB", enabled=True)
    disabled = _project(workspace, create_user, "Disabled", "DISA", enabled=False)

    enabled_issue = Issue.objects.create(name="A", project=enabled, created_by=create_user)
    disabled_issue = Issue.objects.create(name="B", project=disabled, created_by=create_user)

    Worklog.objects.create(
        project=enabled, issue=enabled_issue, logged_by=create_user, created_by=create_user,
        duration=120, logged_at=date(2026, 7, 20),
    )
    Worklog.objects.create(
        project=enabled, issue=enabled_issue, logged_by=create_user, created_by=create_user,
        duration=45, logged_at=date(2026, 7, 25),
    )
    Worklog.objects.create(
        project=disabled, issue=disabled_issue, logged_by=create_user, created_by=create_user,
        duration=999, logged_at=date(2026, 7, 20),
    )
    return {"enabled": enabled, "disabled": disabled}


@pytest.mark.contract
def test_journal_lists_entries(session_client, workspace, seeded):
    response = session_client.get(f"/api/workspaces/{workspace.slug}/worklogs/")
    assert response.status_code == 200
    # This project's `BasePaginator.paginate` (apps/api/plane/utils/paginator.py) returns
    # "count" as the length of the *current page* of results and "total_count" as the
    # true count of matching rows across all pages. With the default per_page of 1000
    # and only a handful of seeded rows, both happen to be equal here, but "total_count"
    # is the semantically correct field to assert the match total against.
    assert response.json()["total_count"] == 2
    assert len(response.json()["results"]) == 2


@pytest.mark.contract
def test_journal_rows_render_readable_fields(session_client, workspace, seeded, create_user):
    """The journal table needs project/issue/person labels, not bare UUIDs —
    and must not leak more about the user than a display name."""
    response = session_client.get(f"/api/workspaces/{workspace.slug}/worklogs/")
    assert response.status_code == 200
    row = response.json()["results"][0]

    enabled_project = seeded["enabled"]
    enabled_issue = enabled_project.project_issue.get(name="A")

    assert row["project"] == str(enabled_project.id)
    assert row["project_name"] == enabled_project.name
    assert row["issue"] == str(enabled_issue.id)
    assert row["issue_identifier"] == f"{enabled_project.identifier}-{enabled_issue.sequence_id}"
    assert row["issue_name"] == enabled_issue.name
    assert row["logged_by"] == str(create_user.id)
    assert row["logged_by_display_name"] == create_user.display_name
    assert "logged_by_email" not in row
    assert "email" not in row


@pytest.mark.contract
def test_journal_hides_projects_with_feature_disabled(session_client, workspace, seeded):
    response = session_client.get(f"/api/workspaces/{workspace.slug}/worklogs/")
    durations = [row["duration"] for row in response.json()["results"]]
    assert 999 not in durations


@pytest.mark.contract
def test_journal_filters_by_date_range(session_client, workspace, seeded):
    response = session_client.get(
        f"/api/workspaces/{workspace.slug}/worklogs/?start_date=2026-07-24&end_date=2026-07-26"
    )
    assert response.json()["total_count"] == 1
    assert response.json()["results"][0]["duration"] == 45


@pytest.mark.contract
def test_journal_filters_by_project(session_client, workspace, seeded):
    response = session_client.get(
        f"/api/workspaces/{workspace.slug}/worklogs/?projects={seeded['enabled'].id}"
    )
    assert response.json()["total_count"] == 2


@pytest.mark.contract
def test_journal_filters_reject_malformed_values_without_crashing(session_client, workspace, seeded):
    """Empty/punctuation-only filter values must not crash the endpoint or
    silently widen the result set (e.g. an empty-string UUID must not become a
    `WHERE ... IN ('')` that matches everything or raises a 500 on cast)."""
    response = session_client.get(
        f"/api/workspaces/{workspace.slug}/worklogs/?users=,&projects=,,&start_date=&end_date="
    )
    assert response.status_code == 200
    assert response.json()["total_count"] == 2


@pytest.mark.contract
def test_journal_unparseable_uuid_filter_alone_returns_400(session_client, workspace, seeded):
    """A filter value that isn't a valid UUID at all must not crash (a raw string
    reaching a UUID column's `__in` lookup raises a database error) and must not
    silently produce a smaller-than-expected total on a billing endpoint — a typo
    should surface as an error, the same way a malformed date does."""
    response = session_client.get(f"/api/workspaces/{workspace.slug}/worklogs/?users=not-a-uuid")
    assert response.status_code == 400


@pytest.mark.contract
def test_journal_unparseable_uuid_mixed_with_valid_one_returns_400(session_client, workspace, seeded):
    """A typo'd token mixed in with a valid id must not be silently dropped
    while the valid one still narrows the results — the whole filter is
    rejected so the caller notices the mistake instead of getting a quietly
    smaller total."""
    response = session_client.get(
        f"/api/workspaces/{workspace.slug}/worklogs/?projects={seeded['enabled'].id},not-a-uuid"
    )
    assert response.status_code == 400


@pytest.mark.contract
def test_journal_malformed_date_returns_400_not_500(session_client, workspace, seeded):
    response = session_client.get(f"/api/workspaces/{workspace.slug}/worklogs/?start_date=not-a-date")
    assert response.status_code == 400


@pytest.mark.contract
def test_summary_totals_match_filter(session_client, workspace, seeded):
    response = session_client.get(f"/api/workspaces/{workspace.slug}/worklogs/summary/")
    assert response.status_code == 200
    assert response.json()["total_duration"] == 165
    assert response.json()["entry_count"] == 2


@pytest.mark.contract
def test_summary_empty_result_returns_zero_not_none(session_client, workspace, seeded):
    """`Sum` over an empty queryset returns ``None`` in Django; the endpoint must
    coerce that to 0 rather than leaking None into the JSON response."""
    response = session_client.get(
        f"/api/workspaces/{workspace.slug}/worklogs/summary/?start_date=2099-01-01&end_date=2099-12-31"
    )
    assert response.status_code == 200
    assert response.json()["total_duration"] == 0
    assert response.json()["entry_count"] == 0


@pytest.mark.contract
def test_journal_closed_for_non_admin(session_client, workspace, seeded, create_user):
    WorkspaceMember.objects.filter(workspace=workspace, member=create_user).update(role=ROLE.MEMBER.value)
    response = session_client.get(f"/api/workspaces/{workspace.slug}/worklogs/")
    assert response.status_code == 403


@pytest.mark.contract
def test_summary_closed_for_non_admin(session_client, workspace, seeded, create_user):
    WorkspaceMember.objects.filter(workspace=workspace, member=create_user).update(role=ROLE.MEMBER.value)
    response = session_client.get(f"/api/workspaces/{workspace.slug}/worklogs/summary/")
    assert response.status_code == 403
