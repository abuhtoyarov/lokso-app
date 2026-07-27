/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/** Matches "2h 30m", "2h", "30m", "2.5h" — hours and minutes both optional, at least one required. */
const DURATION_PATTERN = /^(?:(\d+(?:\.\d+)?)\s*h)?\s*(?:(\d+(?:\.\d+)?)\s*m)?$/i;

/**
 * Reads a human-typed duration into whole minutes.
 *
 * Accepts "2h 30m", "2h", "150m", "2.5h", and a bare number read as minutes.
 * Returns null for anything it cannot read, and for zero — logging no time is
 * not a meaningful entry, and the API rejects it anyway.
 */
export const parseDuration = (input: string): number | null => {
  const trimmed = input.trim();
  if (!trimmed) return null;

  // A bare number means minutes: people type "90" far more often than "90m".
  if (/^\d+(?:\.\d+)?$/.test(trimmed)) {
    const minutes = Math.round(Number(trimmed));
    return minutes > 0 ? minutes : null;
  }

  const match = trimmed.match(DURATION_PATTERN);
  if (!match) return null;

  const [, rawHours, rawMinutes] = match;
  if (rawHours === undefined && rawMinutes === undefined) return null;

  const minutes = Math.round(Number(rawHours ?? 0) * 60 + Number(rawMinutes ?? 0));
  return minutes > 0 ? minutes : null;
};

/**
 * Renders whole minutes as "2h 45m". Hours are not collapsed into days.
 *
 * Named `formatWorklogDuration` rather than `formatDuration` because
 * `./datetime` already exports a `formatDuration(seconds)` with a different
 * signature and unit (seconds, not minutes) — a wildcard re-export of both
 * from `./index` would be an ambiguous-export TS error.
 */
export const formatWorklogDuration = (minutes: number): string => `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
