# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Third Party imports
from rest_framework.permissions import SAFE_METHODS, BasePermission

# Module imports
from plane.db.models import Project, ProjectMember
from plane.db.models.project import ROLE


class WorklogPermission(BasePermission):
    """Time tracking must be enabled on the project, and guests may not log time.

    Object level: the person the time belongs to may edit their own entry;
    project admins may edit anyone's.
    """

    def has_permission(self, request, view):
        if request.user.is_anonymous:
            return False

        if not Project.objects.filter(
            workspace__slug=view.workspace_slug,
            pk=view.project_id,
            is_time_tracking_enabled=True,
            archived_at__isnull=True,
        ).exists():
            return False

        return ProjectMember.objects.filter(
            workspace__slug=view.workspace_slug,
            project_id=view.project_id,
            member=request.user,
            role__in=[ROLE.ADMIN.value, ROLE.MEMBER.value],
            is_active=True,
        ).exists()

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        if obj.logged_by_id == request.user.id:
            return True

        return ProjectMember.objects.filter(
            workspace__slug=view.workspace_slug,
            project_id=view.project_id,
            member=request.user,
            role=ROLE.ADMIN.value,
            is_active=True,
        ).exists()
