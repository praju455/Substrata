"use client";

import { useEffect, useRef, useState } from "react";
import "../platform/workspace.css";
import {
  copyKeys,
  localeTag,
  localizeMessage,
  translate,
  useLocale,
  type CopyKey,
} from "../platform/i18n";

const API = (
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"
).replace(/\/$/, "");

export default function SupplierPortal() {
  const [locale, setLocale] = useLocale();
  const t = (key: Parameters<typeof translate>[1]) => translate(locale, key);
  const tStatus = (value: string) =>
    copyKeys.includes(value as CopyKey) ? t(value as CopyKey) : value;
  const [token, setToken] = useState("");
  // Strict Mode repeats the effect after the first pass removes the fragment.
  // Keep the captured token in memory only; never persist it in browser storage.
  const fragmentToken = useRef<string | null>(null);
  const [request, setRequest] = useState<{
    source: string;
    target: string;
    type: string;
    status: string;
    expires_at: string;
    passages: string[];
  } | null>(null);
  const [responder, setResponder] = useState("");
  const [reason, setReason] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    document.documentElement.lang = localeTag(locale);
  }, [locale]);
  useEffect(() => {
    const controller = new AbortController();
    const load = async () => {
      const value =
        fragmentToken.current ??
        new URLSearchParams(location.hash.slice(1)).get("token") ??
        "";
      fragmentToken.current = value;
      history.replaceState(null, "", location.pathname);
      setToken(value);
      if (!value) {
        setMessage("This link is missing its confirmation token.");
        return;
      }
      const response = await fetch(API + "/platform/supplier-portal/describe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: value }),
        signal: controller.signal,
      });
      const data = await response.json();
      if (!response.ok)
        throw new Error(data.detail || "The link is unavailable or expired.");
      if (!controller.signal.aborted) setRequest(data);
    };
    void load().catch((error) => {
      if (!controller.signal.aborted) setMessage(error.message);
    });
    return () => controller.abort();
  }, []);
  const respond = async (decision: string) => {
    setBusy(true);
    try {
      const response = await fetch(API + "/platform/supplier-portal/reply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, decision, responder, reason }),
      });
      const data = await response.json();
      if (!response.ok)
        throw new Error(data.detail || "Your response could not be recorded.");
      setToken("");
      fragmentToken.current = "";
      setRequest((current) =>
        current ? { ...current, status: decision } : current,
      );
      setMessage(
        "Thank you. Your response has been recorded with its rationale.",
      );
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "The request failed.",
      );
    } finally {
      setBusy(false);
    }
  };
  return (
    <main className="shell main-content platform-workspace">
      <section
        className="panel supplier-portal-panel"
      >
        <p className="eyebrow purple">
          {t("SUBSTRATA · SUPPLIER CONFIRMATION")}
        </p>
        <h1>{t("Review this relationship")}</h1>
        {message && (
          <p className="notice" role="status">
            {localizeMessage(locale, message)}
          </p>
        )}
        <label className="locale-picker">
          <span className="visually-hidden">{t("Language")}</span>
          <select
            aria-label={t("Language")}
            value={locale}
            onChange={(event) => setLocale(event.target.value as "en" | "hi")}
          >
            <option value="en">English</option>
            <option value="hi">हिन्दी</option>
          </select>
        </label>
        {request && (
          <>
            <h2>
              {request.source} → {request.target}
            </h2>
            <p>
              {tStatus(request.type)} ·{" "}
              {localizeMessage(locale, request.status)}
            </p>
            <p className="muted">
              {t(
                "This is a relationship claim for your review. It does not authorise a purchase or operational change.",
              )}
            </p>
            {request.passages.map((passage, i) => (
              <blockquote key={i}>{passage}</blockquote>
            ))}
            <p>
              {t("Link expires")}{" "}
              {new Date(request.expires_at).toLocaleString(localeTag(locale))}.
            </p>
            <label>
              {t("Your name or supplier reference")}
              <input
                value={responder}
                onChange={(e) => setResponder(e.target.value)}
              />
            </label>
            <label>
              {t("Reason")}
              <textarea
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
            </label>
            <div className="button-row">
              <button
                className="primary"
                disabled={busy || !token || !responder.trim() || !reason.trim()}
                onClick={() => void respond("confirmed")}
              >
                {t("Confirm relationship")}
              </button>
              <button
                className="secondary"
                disabled={busy || !token || !responder.trim() || !reason.trim()}
                onClick={() => void respond("rejected")}
              >
                {t("Reject relationship")}
              </button>
            </div>
          </>
        )}
      </section>
    </main>
  );
}
