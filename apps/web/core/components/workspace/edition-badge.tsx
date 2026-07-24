/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// ui
import { useTranslation } from "@plane/i18n";
import { Tooltip } from "@plane/propel/tooltip";
// hooks
import { usePlatformOS } from "@/hooks/use-platform-os";
import packageJson from "package.json";
// local components
import { Button } from "@plane/propel/button";

export const WorkspaceEditionBadge = observer(function WorkspaceEditionBadge() {
  // translation
  const { t } = useTranslation();
  // platform
  const { isMobile } = usePlatformOS();

  // Upgrade modal removed in this fork: the badge is informational only.
  return (
    <Tooltip tooltipContent={`Version: v${packageJson.version}`} isMobile={isMobile}>
      <Button variant="tertiary" size="lg" aria-label={t("aria_labels.projects_sidebar.edition_badge")}>
        Community
      </Button>
    </Tooltip>
  );
});
