# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Contract tests for the worklog CRUD endpoints."""

from datetime import date

import pytest

from plane.db.models import Issue, Project, ProjectMember, Worklog
from plane.db.models.project import ROLE


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(
        name="Test Project",
        identifier="TEST",
        workspace=workspace,
        created_by=create_user,
        is_time_tracking_enabled=True,
    )
    ProjectMember.objects.create(
        project=project, workspace=workspace, member=create_user, role=ROLE.ADMIN.value, is_active=True
    )
    return project


@pytest.fixture
def issue(db, project, create_user):
    return Issue.objects.create(name="Test Issue", project=project, created_by=create_user)


def _list_url(workspace, project, issue):
    return f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/{issue.id}/worklogs/"


def _detail_url(workspace, project, issue, worklog):
    return f"{_list_url(workspace, project, issue)}{worklog.id}/"


@pytest.mark.contract
def test_create_worklog(session_client, workspace, project, issue):
    response = session_client.post(
        _list_url(workspace, project, issue),
        data={"duration": 165, "description": "調査", "logged_at": "2026-07-20"},
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["duration"] == 165
    assert Worklog.objects.count() == 1


@pytest.mark.contract
def test_create_sets_logged_by_to_request_user(session_client, workspace, project, issue, create_user):
    session_client.post(
        _list_url(workspace, project, issue),
        data={"duration": 30, "logged_at": "2026-07-20"},
        format="json",
    )
    worklog = Worklog.objects.get()
    assert worklog.logged_by_id == create_user.id
    assert worklog.created_by_id == create_user.id


@pytest.mark.contract
def test_backdating_is_allowed(session_client, workspace, project, issue):
    response = session_client.post(
        _list_url(workspace, project, issue),
        data={"duration": 60, "logged_at": "2020-01-01"},
        format="json",
    )
    assert response.status_code == 201
    assert str(Worklog.objects.get().logged_at) == "2020-01-01"


@pytest.mark.contract
def test_zero_duration_rejected(session_client, workspace, project, issue):
    response = session_client.post(
        _list_url(workspace, project, issue),
        data={"duration": 0, "logged_at": "2026-07-20"},
        format="json",
    )
    assert response.status_code == 400
    assert Worklog.objects.count() == 0


@pytest.mark.contract
def test_negative_duration_rejected(session_client, workspace, project, issue):
    response = session_client.post(
        _list_url(workspace, project, issue),
        data={"duration": -30, "logged_at": "2026-07-20"},
        format="json",
    )
    assert response.status_code == 400
    assert Worklog.objects.count() == 0


@pytest.mark.contract
def test_api_closed_when_feature_disabled(session_client, workspace, project, issue):
    project.is_time_tracking_enabled = False
    project.save()

    response = session_client.post(
        _list_url(workspace, project, issue),
        data={"duration": 60, "logged_at": "2026-07-20"},
        format="json",
    )
    assert response.status_code == 403

    response = session_client.get(_list_url(workspace, project, issue))
    assert response.status_code == 403


@pytest.mark.contract
def test_disabling_feature_keeps_data(session_client, workspace, project, issue, create_user):
    Worklog.objects.create(
        project=project, issue=issue, logged_by=create_user, created_by=create_user,
        duration=60, logged_at=date(2026, 7, 20),
    )
    project.is_time_tracking_enabled = False
    project.save()
    assert Worklog.objects.count() == 1

    project.is_time_tracking_enabled = True
    project.save()
    response = session_client.get(_list_url(workspace, project, issue))
    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.contract
def test_author_updates_own_entry(session_client, workspace, project, issue, create_user):
    worklog = Worklog.objects.create(
        project=project, issue=issue, logged_by=create_user, created_by=create_user,
        duration=60, logged_at=date(2026, 7, 20),
    )
    response = session_client.patch(
        _detail_url(workspace, project, issue, worklog),
        data={"duration": 90},
        format="json",
    )
    assert response.status_code == 200
    worklog.refresh_from_db()
    assert worklog.duration == 90


@pytest.mark.contract
def test_member_cannot_edit_other_users_entry(session_client, workspace, project, issue, create_user, create_bot_user):
    ProjectMember.objects.filter(project=project, member=create_user).update(role=ROLE.MEMBER.value)
    worklog = Worklog.objects.create(
        project=project, issue=issue, logged_by=create_bot_user, created_by=create_bot_user,
        duration=60, logged_at=date(2026, 7, 20),
    )
    response = session_client.patch(
        _detail_url(workspace, project, issue, worklog),
        data={"duration": 90},
        format="json",
    )
    assert response.status_code == 403
    worklog.refresh_from_db()
    assert worklog.duration == 60


@pytest.mark.contract
def test_project_admin_edits_other_users_entry(session_client, workspace, project, issue, create_bot_user):
    worklog = Worklog.objects.create(
        project=project, issue=issue, logged_by=create_bot_user, created_by=create_bot_user,
        duration=60, logged_at=date(2026, 7, 20),
    )
    response = session_client.patch(
        _detail_url(workspace, project, issue, worklog),
        data={"duration": 90},
        format="json",
    )
    assert response.status_code == 200


@pytest.mark.contract
def test_guest_cannot_log_time(session_client, workspace, project, issue, create_user):
    ProjectMember.objects.filter(project=project, member=create_user).update(role=ROLE.GUEST.value)
    response = session_client.post(
        _list_url(workspace, project, issue),
        data={"duration": 60, "logged_at": "2026-07-20"},
        format="json",
    )
    assert response.status_code == 403


@pytest.mark.contract
def test_guest_can_read_worklogs(session_client, workspace, project, issue, create_user):
    ProjectMember.objects.filter(project=project, member=create_user).update(role=ROLE.GUEST.value)
    Worklog.objects.create(
        project=project, issue=issue, logged_by=create_user, created_by=create_user,
        duration=60, logged_at=date(2026, 7, 20),
    )
    response = session_client.get(_list_url(workspace, project, issue))
    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.contract
def test_guest_cannot_edit_worklog(session_client, workspace, project, issue, create_user):
    ProjectMember.objects.filter(project=project, member=create_user).update(role=ROLE.GUEST.value)
    worklog = Worklog.objects.create(
        project=project, issue=issue, logged_by=create_user, created_by=create_user,
        duration=60, logged_at=date(2026, 7, 20),
    )
    response = session_client.patch(
        _detail_url(workspace, project, issue, worklog),
        data={"duration": 90},
        format="json",
    )
    assert response.status_code == 403
    worklog.refresh_from_db()
    assert worklog.duration == 60
