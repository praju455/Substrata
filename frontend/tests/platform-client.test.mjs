import assert from "node:assert/strict";
import test from "node:test";
import { API, call } from "../app/platform/client.ts";

test("platform calls preserve verified credentials and typed JSON inputs", async () => {
  const original = globalThis.fetch;
  const requests = [];
  globalThis.fetch = async (url, options) => {
    requests.push({ url, options });
    return new Response(JSON.stringify({ status: "pending" }), { status: 200 });
  };
  try {
    assert.deepEqual(
      await call("/jobs", "fixture-access", {
        kind: "event_poll",
        payload: {},
      }),
      { status: "pending" },
    );
    assert.equal(requests[0].url, API + "/platform/jobs");
    assert.equal(
      requests[0].options.headers.Authorization,
      "Bearer fixture-access",
    );
    assert.equal(requests[0].options.method, "POST");
    assert.deepEqual(JSON.parse(requests[0].options.body), {
      kind: "event_poll",
      payload: {},
    });
    await call("/auth/config", "");
    assert.equal(requests[1].options.method, "GET");
    assert.equal(requests[1].options.headers.Authorization, undefined);
    assert.equal(requests[1].options.body, undefined);
    assert.equal(requests[1].options.cache, "no-store");
  } finally {
    globalThis.fetch = original;
  }
});

test("HTTP and JSON-RPC failures never appear as successful workspace actions", async () => {
  const original = globalThis.fetch;
  try {
    globalThis.fetch = async () =>
      new Response(JSON.stringify({ detail: "Role required." }), {
        status: 403,
      });
    await assert.rejects(call("/jobs", "fixture"), /Role required/);
    globalThis.fetch = async () =>
      new Response(
        JSON.stringify({
          jsonrpc: "2.0",
          error: { code: -32602, message: "Graph version is required." },
        }),
        { status: 200 },
      );
    await assert.rejects(
      call("/a2a", "fixture", {}),
      /Graph version is required/,
    );
  } finally {
    globalThis.fetch = original;
  }
});
