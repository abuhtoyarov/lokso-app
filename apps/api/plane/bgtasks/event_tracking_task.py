# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# PostHog event tracking removed in this fork (Lokso). track_event is kept as a
# no-op celery task so existing call sites (workspace views, auth utils) keep
# working without sending anything anywhere.

import uuid
from typing import Dict, Any

# third party imports
from celery import shared_task


@shared_task
def track_event(user_id: uuid.UUID, event_name: str, slug: str, event_properties: Dict[str, Any]):
    """No-op: product analytics (PostHog) has been removed in this fork."""
    return
