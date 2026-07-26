# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Worklog changes must leave an immutable trail in the issue activity feed."""

import pytest

from plane.celery import app as celery_app
from plane.db.models import Issue, IssueActivity, Project, ProjectMember, Worklog
from plane.db.models.project import ROLE


@pytest.fixture(autouse=True)
def _run_celery_tasks_eagerly():
    """Worklog changes fire ``issue_activity.delay(...)``. The test stack has a real
    RabbitMQ broker but no worker consuming it, so without eager mode the task is
    published and never executed, and the activity rows this test asserts on would
    never appear. Running tasks eagerly, in-process, is what actually exercises the
    activity-writing code under test."""
    previous_eager = celery_app.conf.task_always_eager
    previous_propagates = celery_app.conf.task_eager_propagates
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    yield
    celery_app.conf.task_always_eager = previous_eager
    celery_app.conf.task_eager_propagates = previous_propagates


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(
        name="Test Project", identifier="TEST", workspace=workspace,
        created_by=create_user, is_time_tracking_enabled=True,
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


@pytest.mark.contract
def test_creating_worklog_writes_activity(session_client, workspace, project, issue):
    response = session_client.post(
        _list_url(workspace, project, issue),
        data={"duration": 165, "logged_at": "2026-07-20"},
        format="json",
    )
    assert response.status_code == 201

    activity = IssueActivity.objects.get(issue=issue, field="worklog")
    assert activity.verb == "created"
    assert activity.new_value == "165"
    assert str(activity.new_identifier) == response.json()["id"]


@pytest.mark.contract
def test_updating_worklog_records_old_and_new(session_client, workspace, project, issue):
    created = session_client.post(
        _list_url(workspace, project, issue),
        data={"duration": 60, "logged_at": "2026-07-20"},
        format="json",
    ).json()

    session_client.patch(
        f"{_list_url(workspace, project, issue)}{created['id']}/",
        data={"duration": 90},
        format="json",
    )

    activity = IssueActivity.objects.get(issue=issue, field="worklog", verb="updated")
    assert activity.old_value == "60"
    assert activity.new_value == "90"


@pytest.mark.contract
def test_updating_only_logged_at_records_activity(session_client, workspace, project, issue):
    created = session_client.post(
        _list_url(workspace, project, issue),
        data={"duration": 60, "logged_at": "2026-07-20"},
        format="json",
    ).json()

    session_client.patch(
        f"{_list_url(workspace, project, issue)}{created['id']}/",
        data={"logged_at": "2026-07-22"},
        format="json",
    )

    activity = IssueActivity.objects.get(issue=issue, field="worklog_logged_at", verb="updated")
    assert activity.old_value == "2026-07-20"
    assert activity.new_value == "2026-07-22"
    assert str(activity.new_identifier) == created["id"]


@pytest.mark.contract
def test_updating_only_description_records_activity(session_client, workspace, project, issue):
    created = session_client.post(
        _list_url(workspace, project, issue),
        data={"duration": 60, "logged_at": "2026-07-20", "description": "initial note"},
        format="json",
    ).json()

    session_client.patch(
        f"{_list_url(workspace, project, issue)}{created['id']}/",
        data={"description": "revised note"},
        format="json",
    )

    activity = IssueActivity.objects.get(issue=issue, field="worklog_description", verb="updated")
    assert activity.old_value == "initial note"
    assert activity.new_value == "revised note"
    assert str(activity.new_identifier) == created["id"]


@pytest.mark.contract
def test_updating_duration_and_logged_at_together_records_both(session_client, workspace, project, issue):
    created = session_client.post(
        _list_url(workspace, project, issue),
        data={"duration": 60, "logged_at": "2026-07-20"},
        format="json",
    ).json()

    session_client.patch(
        f"{_list_url(workspace, project, issue)}{created['id']}/",
        data={"duration": 90, "logged_at": "2026-07-22"},
        format="json",
    )

    duration_activity = IssueActivity.objects.get(issue=issue, field="worklog", verb="updated")
    assert duration_activity.old_value == "60"
    assert duration_activity.new_value == "90"

    date_activity = IssueActivity.objects.get(issue=issue, field="worklog_logged_at", verb="updated")
    assert date_activity.old_value == "2026-07-20"
    assert date_activity.new_value == "2026-07-22"


@pytest.mark.contract
def test_updating_worklog_with_no_changes_records_no_activity(session_client, workspace, project, issue):
    created = session_client.post(
        _list_url(workspace, project, issue),
        data={"duration": 60, "logged_at": "2026-07-20", "description": "same note"},
        format="json",
    ).json()

    before_count = IssueActivity.objects.filter(issue=issue, verb="updated").count()

    session_client.patch(
        f"{_list_url(workspace, project, issue)}{created['id']}/",
        data={"duration": 60, "logged_at": "2026-07-20", "description": "same note"},
        format="json",
    )

    after_count = IssueActivity.objects.filter(issue=issue, verb="updated").count()
    assert after_count == before_count


@pytest.mark.contract
def test_deleting_worklog_keeps_its_activity(session_client, workspace, project, issue):
    created = session_client.post(
        _list_url(workspace, project, issue),
        data={"duration": 60, "logged_at": "2026-07-20"},
        format="json",
    ).json()

    session_client.delete(f"{_list_url(workspace, project, issue)}{created['id']}/")

    assert Worklog.objects.count() == 0
    assert IssueActivity.objects.filter(issue=issue, field="worklog", verb="created").exists()
    assert IssueActivity.objects.filter(issue=issue, field="worklog", verb="deleted").exists()
