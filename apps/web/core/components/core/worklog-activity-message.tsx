/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useTranslation } from "@plane/i18n";
import type { IIssueActivity } from "@plane/types";
import { formatWorklogDuration, renderFormattedDate } from "@plane/utils";
import { IssueLink } from "./activity-issue-link";

type Props = {
  activity: IIssueActivity;
  showIssue: boolean;
};

export function WorklogActivityMessage({ activity, showIssue }: Props) {
  const { t } = useTranslation();

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
    <>
      {message}
      {showIssue && (
        <>
          {" "}
          {t("worklog.activity.for_issue")} <IssueLink activity={activity} />
        </>
      )}
    </>
  );
}
