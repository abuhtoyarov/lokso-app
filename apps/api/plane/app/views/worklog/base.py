# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import json
import uuid

# Third Party imports
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count, Sum
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.exceptions import ParseError
from rest_framework.response import Response

# Module imports
from plane.app.permissions import allow_permission, ROLE, WorklogPermission
from plane.app.serializers import ExporterHistorySerializer, WorklogJournalSerializer, WorklogSerializer
from plane.bgtasks.issue_activities_task import issue_activity
from plane.bgtasks.worklog_export_task import worklog_export_task
from plane.db.models import ExporterHistory, Worklog, Workspace

from .. import BaseAPIView, BaseViewSet


class WorklogViewSet(BaseViewSet):
    permission_classes = [WorklogPermission]

    model = Worklog
    serializer_class = WorklogSerializer

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(workspace__slug=self.kwargs.get("slug"))
            .filter(project_id=self.kwargs.get("project_id"))
            .filter(issue_id=self.kwargs.get("issue_id"))
            .filter(
                project__project_projectmember__member=self.request.user,
                project__project_projectmember__is_active=True,
                project__archived_at__isnull=True,
            )
            .select_related("logged_by")
            .distinct()
        )

    def create(self, request, slug, project_id, issue_id):
        serializer = WorklogSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(project_id=project_id, issue_id=issue_id, logged_by=request.user)
            issue_activity.delay(
                type="worklog.activity.created",
                requested_data=json.dumps(serializer.data, cls=DjangoJSONEncoder),
                actor_id=str(request.user.id),
                issue_id=str(issue_id),
                project_id=str(project_id),
                current_instance=None,
                epoch=int(timezone.now().timestamp()),
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, slug, project_id, issue_id, pk):
        worklog = self.get_queryset().get(pk=pk)
        self.check_object_permissions(request, worklog)
        current_instance = json.dumps(WorklogSerializer(worklog).data, cls=DjangoJSONEncoder)

        serializer = WorklogSerializer(worklog, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            issue_activity.delay(
                type="worklog.activity.updated",
                requested_data=json.dumps(serializer.data, cls=DjangoJSONEncoder),
                actor_id=str(request.user.id),
                issue_id=str(issue_id),
                project_id=str(project_id),
                current_instance=current_instance,
                epoch=int(timezone.now().timestamp()),
            )
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, slug, project_id, issue_id, pk):
        worklog = self.get_queryset().get(pk=pk)
        self.check_object_permissions(request, worklog)
        current_instance = json.dumps(WorklogSerializer(worklog).data, cls=DjangoJSONEncoder)
        worklog.delete()
        issue_activity.delay(
            type="worklog.activity.deleted",
            requested_data=None,
            actor_id=str(request.user.id),
            issue_id=str(issue_id),
            project_id=str(project_id),
            current_instance=current_instance,
            epoch=int(timezone.now().timestamp()),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


def _apply_uuid_list_filter(queryset, field_lookup, raw_value, param_name):
    """Filter ``queryset`` by a comma-separated list of UUIDs from a query param.

    Filters arrive as raw, user-controlled strings, so this has to handle a few
    cases without crashing:

    - Not provided / blank (``None``, ``""``): no filter is applied.
    - Provided but only punctuation (``","``, ``",,"``), or with stray
      whitespace/empty segments (``"a,,b"``, trailing ``","``): those blank
      segments are formatting noise, not typos, and are dropped silently. If
      nothing is left after dropping them, that's the same as "not provided".
    - Provided with a token that isn't a valid UUID at all (``"not-a-uuid"``):
      this is a typo, not formatting noise. Passing it straight to ``__in``
      would raise a database error on a UUID column, and silently dropping it
      (or silently matching nothing) would let a mistyped id quietly change a
      billing total without telling the caller. So this raises a 400 instead,
      the same way a malformed date does.
    """
    if not raw_value:
        return queryset

    tokens = [token.strip() for token in raw_value.split(",") if token.strip()]
    if not tokens:
        return queryset

    for token in tokens:
        try:
            uuid.UUID(token)
        except (ValueError, AttributeError, TypeError) as exc:
            raise ParseError(detail=f"Invalid {param_name} value. '{token}' is not a valid UUID.") from exc

    return queryset.filter(**{field_lookup: tokens})


def _parse_date_param(value, param_name):
    """Parse a ``YYYY-MM-DD`` query parameter, rejecting malformed input with a 400.

    ``parse_date`` returns ``None`` for strings that aren't date-shaped at all,
    and raises ``ValueError`` for date-shaped strings with out-of-range
    components (e.g. month 13). Either way, a malformed date must not reach the
    ORM: filtering a ``DateField`` with an unparseable value raises Django's
    ``django.core.exceptions.ValidationError``, which DRF's exception handler
    does not translate into a response, so it surfaces as an unhandled 500.
    """
    if not value:
        return None
    try:
        parsed = parse_date(value)
    except ValueError:
        parsed = None
    if parsed is None:
        raise ParseError(detail=f"Invalid {param_name} value. Expected YYYY-MM-DD.")
    return parsed


class WorkspaceWorklogEndpoint(BaseAPIView):
    """Workspace-wide worklog journal for workspace admins.

    Shows logged time across every project in the workspace, excluding
    archived projects and projects with time tracking disabled, so the
    figures an admin sees here always match what the team sees per-project.
    """

    def _filtered_queryset(self, request, slug):
        queryset = Worklog.objects.filter(
            workspace__slug=slug,
            project__is_time_tracking_enabled=True,
            project__archived_at__isnull=True,
        ).select_related("project", "issue", "logged_by")

        queryset = _apply_uuid_list_filter(queryset, "logged_by_id__in", request.GET.get("users"), "users")
        queryset = _apply_uuid_list_filter(queryset, "project_id__in", request.GET.get("projects"), "projects")

        start_date = _parse_date_param(request.GET.get("start_date"), "start_date")
        if start_date:
            queryset = queryset.filter(logged_at__gte=start_date)

        end_date = _parse_date_param(request.GET.get("end_date"), "end_date")
        if end_date:
            queryset = queryset.filter(logged_at__lte=end_date)

        return queryset

    #: Columns the journal serializer actually reads. Passed to ``.only()`` so
    #: the ``select_related`` joins in ``_filtered_queryset`` stop pulling
    #: every column of the joined rows (e.g. ``issues.description_binary``,
    #: ``issues.description_html``, ``users.password``) just to discard them.
    JOURNAL_ONLY_FIELDS = (
        "id",
        "duration",
        "logged_at",
        "description",
        "project_id",
        "issue_id",
        "logged_by_id",
        "project__name",
        "project__identifier",
        "issue__name",
        "issue__sequence_id",
        "logged_by__display_name",
    )

    @allow_permission(allowed_roles=[ROLE.ADMIN], level="WORKSPACE")
    def get(self, request, slug):
        queryset = self._filtered_queryset(request, slug).only(*self.JOURNAL_ONLY_FIELDS)
        return self.paginate(
            request=request,
            queryset=queryset,
            on_results=lambda worklogs: WorklogJournalSerializer(worklogs, many=True).data,
        )


class WorkspaceWorklogSummaryEndpoint(WorkspaceWorklogEndpoint):
    """Total logged time for the same filters as :class:`WorkspaceWorklogEndpoint`.

    Subclasses the journal endpoint purely to reuse ``_filtered_queryset`` — the
    ``@allow_permission`` decorator on the parent's ``get`` is not inherited by
    this override, so it is re-applied here explicitly.
    """

    @allow_permission(allowed_roles=[ROLE.ADMIN], level="WORKSPACE")
    def get(self, request, slug):
        aggregate = self._filtered_queryset(request, slug).aggregate(
            total_duration=Sum("duration"), entry_count=Count("id")
        )
        return Response(
            {
                "total_duration": aggregate["total_duration"] or 0,
                "entry_count": aggregate["entry_count"] or 0,
            },
            status=status.HTTP_200_OK,
        )


class WorklogExportEndpoint(BaseAPIView):
    serializer_class = ExporterHistorySerializer

    @allow_permission(allowed_roles=[ROLE.ADMIN], level="WORKSPACE")
    def post(self, request, slug):
        provider = request.data.get("provider", False)
        if provider not in ["csv", "xlsx", "json"]:
            return Response(
                {"error": f"Provider '{provider}' not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        workspace = Workspace.objects.get(slug=slug)
        filters = {
            key: request.data.get(key)
            for key in ("users", "projects", "start_date", "end_date")
            if request.data.get(key)
        }

        exporter = ExporterHistory.objects.create(
            workspace=workspace,
            initiated_by=request.user,
            provider=provider,
            type="issue_worklogs",
            filters=filters,
        )

        worklog_export_task.delay(
            provider=exporter.provider,
            workspace_id=workspace.id,
            token_id=exporter.token,
            slug=slug,
            filters=filters,
        )
        return Response(
            {"message": "Once the export is ready you will be able to download it"},
            status=status.HTTP_200_OK,
        )

    @allow_permission(allowed_roles=[ROLE.ADMIN], level="WORKSPACE")
    def get(self, request, slug):
        exporter_history = ExporterHistory.objects.filter(
            workspace__slug=slug, type="issue_worklogs"
        ).select_related("workspace", "initiated_by")

        return self.paginate(
            order_by=request.GET.get("order_by", "-created_at"),
            request=request,
            queryset=exporter_history,
            on_results=lambda rows: ExporterHistorySerializer(rows, many=True).data,
        )
