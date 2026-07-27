/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { useTranslation } from "@plane/i18n";
import { Button, Input, TextArea } from "@plane/ui";
import { formatWorklogDuration, parseDuration, renderFormattedPayloadDate } from "@plane/utils";
import type { TWorklog } from "@plane/types";

type TLogWorkFormProps = {
  /** Present when editing an existing entry, absent when logging a new one. */
  entry?: TWorklog;
  onCancel: () => void;
  onSubmit: (data: Pick<TWorklog, "duration" | "description" | "logged_at">) => Promise<void>;
};

const todayPayloadDate = () => renderFormattedPayloadDate(new Date()) ?? "";

export function WorklogLogWorkForm(props: TLogWorkFormProps) {
  const { entry, onCancel, onSubmit } = props;
  const { t } = useTranslation();
  // form state
  const [durationInput, setDurationInput] = useState(entry ? formatWorklogDuration(entry.duration) : "");
  const [loggedAt, setLoggedAt] = useState(entry?.logged_at ?? todayPayloadDate());
  const [description, setDescription] = useState(entry?.description ?? "");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (isSubmitting) return;

    const duration = parseDuration(durationInput);
    if (duration === null) {
      setError(t("worklog.invalid_duration"));
      return;
    }

    setError(null);
    setIsSubmitting(true);
    try {
      await onSubmit({ duration, description, logged_at: loggedAt || todayPayloadDate() });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex w-full flex-col gap-2 rounded-md border border-subtle-1 p-2">
      <div className="flex flex-wrap items-center gap-2">
        <Input
          id="worklog-duration"
          name="duration"
          type="text"
          value={durationInput}
          onChange={(event) => {
            setDurationInput(event.target.value);
            if (error) setError(null);
          }}
          placeholder="2h 30m"
          hasError={Boolean(error)}
          className="w-28 px-2 py-1 text-body-xs-regular"
        />
        <Input
          id="worklog-logged-at"
          name="logged_at"
          type="date"
          value={loggedAt}
          max={todayPayloadDate()}
          onChange={(event) => setLoggedAt(event.target.value)}
          className="px-2 py-1 text-body-xs-regular"
        />
      </div>
      {error && <span className="text-body-xs-regular text-danger-primary">{error}</span>}
      <TextArea
        id="worklog-description"
        name="description"
        value={description}
        onChange={(event) => setDescription(event.target.value)}
        placeholder={t("worklog.description")}
        textAreaSize="sm"
        className="w-full text-body-xs-regular"
      />
      <div className="flex items-center justify-end gap-2">
        <Button type="button" variant="neutral-primary" size="sm" onClick={onCancel} disabled={isSubmitting}>
          {t("worklog.cancel")}
        </Button>
        <Button type="submit" variant="primary" size="sm" loading={isSubmitting}>
          {t("worklog.save")}
        </Button>
      </div>
    </form>
  );
}
