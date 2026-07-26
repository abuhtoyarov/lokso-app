# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Unit tests for the Worklog model."""

from datetime import date

import pytest
from django.db.utils import IntegrityError

from plane.db.models import Issue, Project, Worklog


@pytest.fixture
def project(db, workspace, create_user):
    return Project.objects.create(
        name="Test Project",
        identifier="TEST",
        workspace=workspace,
        created_by=create_user,
        is_time_tracking_enabled=True,
    )


@pytest.fixture
def issue(db, project, create_user):
    return Issue.objects.create(name="Test Issue", project=project, created_by=create_user)


@pytest.mark.unit
def test_worklog_sets_workspace_from_project(db, project, issue, create_user):
    worklog = Worklog.objects.create(
        project=project,
        issue=issue,
        logged_by=create_user,
        created_by=create_user,
        duration=165,
        logged_at=date(2026, 7, 20),
    )
    assert worklog.workspace_id == project.workspace_id
    assert worklog.duration == 165


@pytest.mark.unit
def test_worklog_rejects_zero_duration(db, project, issue, create_user):
    with pytest.raises(IntegrityError):
        Worklog.objects.create(
            project=project,
            issue=issue,
            logged_by=create_user,
            created_by=create_user,
            duration=0,
            logged_at=date(2026, 7, 20),
        )


@pytest.mark.unit
def test_worklog_keeps_logged_by_separate_from_created_by(db, project, issue, create_user, create_bot_user):
    worklog = Worklog.objects.create(
        project=project,
        issue=issue,
        logged_by=create_bot_user,
        created_by=create_user,
        duration=30,
        logged_at=date(2026, 7, 20),
    )
    assert worklog.logged_by_id != worklog.created_by_id
