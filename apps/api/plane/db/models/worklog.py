# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.conf import settings
from django.db import models

# Module imports
from .project import ProjectBaseModel


class Worklog(ProjectBaseModel):
    """A single logged time entry against a work item.

    Duration is stored in whole minutes. ``logged_at`` is the date the work was
    performed and may be backdated; ``created_at`` records when the entry was
    entered, so the pair forms an audit trail.
    """

    issue = models.ForeignKey("db.Issue", on_delete=models.CASCADE, related_name="issue_worklogs")
    logged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user_worklogs",
    )
    duration = models.PositiveIntegerField(verbose_name="Duration in minutes")
    description = models.TextField(blank=True)
    logged_at = models.DateField(verbose_name="Date the work was performed")

    class Meta:
        verbose_name = "Worklog"
        verbose_name_plural = "Worklogs"
        db_table = "worklogs"
        ordering = ("-logged_at", "-created_at")
        constraints = [
            models.CheckConstraint(check=models.Q(duration__gt=0), name="worklog_duration_positive")
        ]

    def __str__(self):
        return f"{self.issue.name} {self.duration}m"
