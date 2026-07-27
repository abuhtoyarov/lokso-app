/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { Timer } from "lucide-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { formatWorklogDuration, renderFormattedDate } from "@plane/utils";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
// components
import { IssueActivityBlockComponent, IssueLink } from "./";

type TIssueWorklogActivity = { activityId: string; showIssue?: boolean; ends: "top" | "bottom" | undefined };

export const IssueWorklogActivity = observer(function IssueWorklogActivity(props: TIssueWorklogActivity) {
  const { activityId, showIssue = false, ends } = props;
  // hooks
  const {
    activity: { getActivityById },
  } = useIssueDetail();
  const { t } = useTranslation();

  const activity = getActivityById(activityId);

  if (!activity) return <></>;

  let message: string;
  if (activity.field === "worklog") {
    if (activity.verb === "created") {
      message = t("worklog.activity.created", { duration: formatWorklogDuration(Number(activity.new_value)) });
    } else if (activity.verb === "updated") {
      message = t("worklog.activity.updated", {
        old: formatWorklogDuration(Number(activity.old_value)),
        new: formatWorklogDuration(Number(activity.new_value)),
      });
    } else {
      message = t("worklog.activity.deleted", { duration: formatWorklogDuration(Number(activity.old_value)) });
    }
  } else if (activity.field === "worklog_logged_at") {
    message = t("worklog.activity.logged_at_updated", {
      old: renderFormattedDate(activity.old_value ?? ""),
      new: renderFormattedDate(activity.new_value ?? ""),
    });
  } else {
    message = t("worklog.activity.description_updated");
  }

  return (
    <IssueActivityBlockComponent
      icon={<Timer size={14} className="text-secondary" aria-hidden="true" />}
      activityId={activityId}
      ends={ends}
    >
      <>
        <span>{message}</span>
        {showIssue && ` for `}
        {showIssue && <IssueLink activityId={activityId} />}.
      </>
    </IssueActivityBlockComponent>
  );
});
