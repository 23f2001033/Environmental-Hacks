// Same-origin API (docs/API.md). CloudFront routes /api/* to the backend.
const BASE = "/api/v1";

async function request(path, options = {}) {
  const res = await fetch(BASE + path, {
    ...options,
    headers: { "content-type": "application/json", ...(options.headers || {}) },
  });
  const text = await res.text();
  let body = null;
  try { body = text ? JSON.parse(text) : null; } catch { body = { error: text }; }
  if (!res.ok) {
    const err = new Error((body && body.error) || `HTTP ${res.status}`);
    err.status = res.status;
    throw err;
  }
  return body;
}

export const get = (path) => request(path);
export const post = (path, body) => request(path, { method: "POST", body: JSON.stringify(body || {}) });

// Signed links (?k=...) are remembered per role and place, so a notification tap opens a working page.
export function linkToken(role, key, search) {
  const storeKey = `jalsaathi-k-${role}-${key}`;
  const fromUrl = new URLSearchParams(search).get("k");
  try {
    if (fromUrl) localStorage.setItem(storeKey, fromUrl);
    return fromUrl || localStorage.getItem(storeKey) || "";
  } catch {
    return fromUrl || "";
  }
}

// Resize a camera photo to a JPEG under ~1 MB before upload (low-end phones, slow networks).
export async function toJpeg(file, max = 1280) {
  const bitmap = await createImageBitmap(file);
  const scale = Math.min(1, max / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(bitmap.width * scale);
  canvas.height = Math.round(bitmap.height * scale);
  canvas.getContext("2d").drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  return new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.85));
}
