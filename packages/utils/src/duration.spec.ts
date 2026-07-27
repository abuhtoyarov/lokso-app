/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { formatWorklogDuration, parseDuration } from "./duration";

describe("parseDuration", () => {
  it("reads hours and minutes", () => {
    expect(parseDuration("2h 30m")).toBe(150);
    expect(parseDuration("2h30m")).toBe(150);
    expect(parseDuration("2 h 30 m")).toBe(150);
  });

  it("reads hours alone", () => {
    expect(parseDuration("2h")).toBe(120);
    expect(parseDuration("2.5h")).toBe(150);
    expect(parseDuration("0.25h")).toBe(15);
  });

  it("reads minutes alone", () => {
    expect(parseDuration("150m")).toBe(150);
    expect(parseDuration("45m")).toBe(45);
  });

  it("reads a bare number as minutes", () => {
    expect(parseDuration("90")).toBe(90);
  });

  it("is case insensitive and tolerates surrounding space", () => {
    expect(parseDuration("  2H 30M  ")).toBe(150);
  });

  it("rejects what it cannot read", () => {
    expect(parseDuration("")).toBeNull();
    expect(parseDuration("abc")).toBeNull();
    expect(parseDuration("-30")).toBeNull();
    expect(parseDuration("2h -30m")).toBeNull();
    expect(parseDuration("h m")).toBeNull();
  });

  it("rejects zero — a worklog of no time is not a worklog", () => {
    expect(parseDuration("0")).toBeNull();
    expect(parseDuration("0h 0m")).toBeNull();
  });

  it("rounds fractional minutes rather than storing a fraction", () => {
    expect(parseDuration("1.51h")).toBe(91);
  });
});

describe("formatDuration", () => {
  it("renders hours and minutes", () => {
    expect(formatWorklogDuration(165)).toBe("2h 45m");
    expect(formatWorklogDuration(120)).toBe("2h 0m");
    expect(formatWorklogDuration(45)).toBe("0h 45m");
    expect(formatWorklogDuration(0)).toBe("0h 0m");
  });

  it("handles durations beyond a day without inventing day units", () => {
    expect(formatWorklogDuration(1500)).toBe("25h 0m");
  });
});
