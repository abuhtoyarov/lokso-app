/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import * as React from "react";

import type { ISvgIcons } from "../type";

export function LoksoLogo({ width = "16", height = "16", className, color = "currentColor" }: ISvgIcons) {
  return (
    <svg
      width={width}
      height={height}
      viewBox="0 0 16 16"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      role="img"
      aria-label="Локсо"
    >
      <rect x="1.5" y="3" width="13" height="2.6" rx="1.3" fill={color} />
      <rect x="1.5" y="6.7" width="9.5" height="2.6" rx="1.3" fill={color} opacity="0.62" />
      <rect x="1.5" y="10.4" width="6" height="2.6" rx="1.3" fill={color} opacity="0.35" />
    </svg>
  );
}
