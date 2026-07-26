# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Third Party imports
from rest_framework import serializers

# Module imports
from plane.db.models import Worklog

from .base import BaseSerializer


class WorklogSerializer(BaseSerializer):
    class Meta:
        model = Worklog
        fields = [
            "id",
            "issue",
            "project",
            "workspace",
            "logged_by",
            "duration",
            "description",
            "logged_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "issue",
            "project",
            "workspace",
            "logged_by",
            "created_at",
            "updated_at",
        ]

    def validate_duration(self, value):
        if value is None or value <= 0:
            raise serializers.ValidationError("Duration must be a positive number of minutes.")
        return value


class WorklogJournalSerializer(BaseSerializer):
    """Read-only serializer for the workspace-wide worklog journal.

    Renders what the journal table actually needs — human-readable project,
    issue and person labels alongside the raw ids the frontend filters by —
    so the client doesn't have to do a lookup per row. Deliberately narrower
    than what a per-project ``Worklog`` payload could expose: no email, no
    audit timestamps, nothing beyond what an admin sees in the billing table.
    """

    project_name = serializers.CharField(source="project.name", read_only=True)
    issue_identifier = serializers.SerializerMethodField()
    issue_name = serializers.CharField(source="issue.name", read_only=True)
    logged_by_display_name = serializers.CharField(source="logged_by.display_name", read_only=True)

    class Meta:
        model = Worklog
        fields = [
            "id",
            "project",
            "project_name",
            "issue",
            "issue_identifier",
            "issue_name",
            "logged_by",
            "logged_by_display_name",
            "duration",
            "logged_at",
            "description",
        ]
        read_only_fields = fields

    def get_issue_identifier(self, obj):
        return f"{obj.project.identifier}-{obj.issue.sequence_id}"
