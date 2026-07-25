# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Telemetry removed in this fork (Lokso). Kept as a no-op stub so existing
# imports (e.g. management commands) do not break.

# Third party imports
from celery import shared_task


@shared_task
def push_instance_metrics():
    """No-op: instance telemetry has been removed in this fork."""
    return
