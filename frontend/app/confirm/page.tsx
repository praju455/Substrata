"use client";

import { useEffect, useState } from "react";
import "../platform/workspace.css";

const API = (
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"
).replace(/\/$/, "");

export default function SupplierPortal() {
  const [token, setToken] = useState("");
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
    const load = async () => {
      const value =
        new URLSearchParams(location.hash.slice(1)).get("token") || "";
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
      });
      const data = await response.json();
      if (!response.ok)
        throw new Error(data.detail || "The link is unavailable or expired.");
      setRequest(data);
    };
    void load().catch((error) => setMessage(error.message));
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
        className="panel"
        style={{ padding: 28, maxWidth: 720, margin: "auto" }}
      >
        <p className="eyebrow purple">SUBSTRATA · SUPPLIER CONFIRMATION</p>
        <h1>Review this relationship</h1>
        {message && (
          <p className="notice" role="status">
            {message}
          </p>
        )}
        {request && (
          <>
            <h2>
              {request.source} → {request.target}
            </h2>
            <p>
              {request.type.replaceAll("_", " ")} · {request.status}
            </p>
            <p className="muted">
              This is a relationship claim for your review. It does not
              authorise a purchase or operational change.
            </p>
            {request.passages.map((passage, i) => (
              <blockquote key={i}>{passage}</blockquote>
            ))}
            <p>Link expires {new Date(request.expires_at).toLocaleString()}.</p>
            <label>
              Your name or supplier reference
              <input
                value={responder}
                onChange={(e) => setResponder(e.target.value)}
              />
            </label>
            <label>
              Reason
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
                Confirm relationship
              </button>
              <button
                className="secondary"
                disabled={busy || !token || !responder.trim() || !reason.trim()}
                onClick={() => void respond("rejected")}
              >
                Reject relationship
              </button>
            </div>
          </>
        )}
      </section>
    </main>
  );
}
