/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { formatWorklogDuration } from "@plane/utils";

type Props = {
  /** Whole minutes. Always a number — `0` on an empty result, never `null`. Must come from `total_duration`. */
  totalDuration: number;
};

export const WorklogJournalSummary = observer(function WorklogJournalSummary(props: Props) {
  const { totalDuration } = props;
  // translation
  const { t } = useTranslation();

  return (
    <div className="text-14 font-medium text-primary">
      {t("workspace_settings.settings.worklogs.total", { duration: formatWorklogDuration(totalDuration) })}
    </div>
  );
});
