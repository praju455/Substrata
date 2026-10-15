"use client";

import { useState } from "react";
import { call } from "./client";
import { translate, useLocale, type CopyKey } from "./i18n";

type Props = {
  token: string;
  actionId: string;
  busy: boolean;
  canDelegate: boolean;
  run: (operation: () => Promise<unknown>) => Promise<void>;
};

export default function Delegation({
  token,
  actionId,
  busy,
  canDelegate,
  run,
}: Props) {
  const [locale] = useLocale();
  const t = (key: CopyKey) => translate(locale, key);
  const [subject, setSubject] = useState("");
  const [reason, setReason] = useState("");
  return (
    <details className="delegation-form">
      <summary>{t("Delegate approval review")}</summary>
      <p className="muted">
        {t(
          "Use the reviewer's identity-provider subject. Delegation does not grant a role or approve the action.",
        )}
      </p>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void run(async () => {
            await call(
              `/approvals/${encodeURIComponent(actionId)}/delegate`,
              token,
              { subject: subject.trim(), reason: reason.trim() },
            );
            setSubject("");
            setReason("");
          });
        }}
      >
        <label>
          {t("Reviewer subject")}
          <input
            required
            maxLength={256}
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
          />
        </label>
        <label>
          {t("Delegation reason")}
          <textarea
            required
            maxLength={2000}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </label>
        <button
          className="secondary"
          disabled={busy || !canDelegate || !subject.trim() || !reason.trim()}
        >
          {t("Delegate review")}
        </button>
      </form>
    </details>
  );
}
