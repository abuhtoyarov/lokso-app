/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import * as React from "react";

import type { ISvgIcons } from "../type";

export function LoksoLockup({ width = "95", height = "20", className, color = "currentColor" }: ISvgIcons) {
  return (
    <svg
      width={width}
      height={height}
      viewBox="0 0 95 20"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      role="img"
      aria-label="Локсо"
    >
      <rect x="2" y="5" width="13" height="2.6" rx="1.3" fill={color} />
      <rect x="2" y="8.7" width="9.5" height="2.6" rx="1.3" fill={color} opacity="0.62" />
      <rect x="2" y="12.4" width="6" height="2.6" rx="1.3" fill={color} opacity="0.35" />
      <text
        x="19.5"
        y="15"
        fontFamily="ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
        fontSize="13.5"
        fontWeight="650"
        letterSpacing="-0.3"
        fill={color}
      >
        Локсо
      </text>
    </svg>
  );
}
