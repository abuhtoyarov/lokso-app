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
