# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Third Party imports
from rest_framework import serializers

# Module imports
from plane.db.models import Worklog


class WorklogExportSerializer(serializers.ModelSerializer):
    """Flat, human-readable shape for CSV and Excel output."""

    project_name = serializers.CharField(source="project.name", read_only=True)
    issue_identifier = serializers.SerializerMethodField()
    issue_name = serializers.CharField(source="issue.name", read_only=True)
    logged_by_name = serializers.CharField(source="logged_by.display_name", read_only=True)
    logged_by_email = serializers.CharField(source="logged_by.email", read_only=True)
    duration_display = serializers.SerializerMethodField()

    class Meta:
        model = Worklog
        fields = [
            "project_name",
            "issue_identifier",
            "issue_name",
            "logged_by_name",
            "logged_by_email",
            "logged_at",
            "duration",
            "duration_display",
            "description",
        ]

    def get_issue_identifier(self, obj):
        return f"{obj.project.identifier}-{obj.issue.sequence_id}"

    def get_duration_display(self, obj):
        return f"{obj.duration // 60}h {obj.duration % 60}m"
