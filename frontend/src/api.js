export async function get(path, { demo = false, signal } = {}) {
  if (demo) {
    const { mockGet } = await import("./mock.js");
    if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
    return mockGet(path);
  }
  const controller = new AbortController();
  const abort = () => controller.abort();
  signal?.addEventListener("abort", abort, { once: true });
  if (signal?.aborted) abort();
  const timeout = setTimeout(abort, 15000);
  try {
    const response = await fetch(`/api/v1${path}`, {
      signal: controller.signal,
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    if (!response.ok)
      throw Object.assign(new Error("Request failed"), {
        status: response.status,
      });
    const data = await response.json();
    return data;
  } finally {
    clearTimeout(timeout);
    signal?.removeEventListener("abort", abort);
  }
}
