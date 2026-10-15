export const API = (
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"
).replace(/\/$/, "");

export async function call(path: string, token: string, body?: unknown) {
  const response = await fetch(API + "/platform" + path, {
    method: body === undefined ? "GET" : "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: "Bearer " + token } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
  });
  const data = await response.json();
  if (!response.ok || data?.error)
    throw new Error(
      typeof data?.detail === "string"
        ? data.detail
        : typeof data?.error?.message === "string"
          ? data.error.message
          : "Check the entered values and permissions.",
    );
  return data;
}
