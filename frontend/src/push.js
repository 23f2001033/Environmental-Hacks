// App notifications (Web Push). The backend signs and encrypts per RFC 8291/8292; this subscribes the browser.
import { get, post } from "./api.js";

export function pushSupported() {
  return typeof window !== "undefined" && "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
}

function keyBytes(base64url) {
  const pad = "=".repeat((4 - (base64url.length % 4)) % 4);
  const raw = atob((base64url + pad).replace(/-/g, "+").replace(/_/g, "/"));
  return Uint8Array.from(raw, (c) => c.charCodeAt(0));
}

const storeKey = (scope, key) => `jalsaathi-push-${scope}-${key}`;

export function isSubscribed(scope, key) {
  try { return localStorage.getItem(storeKey(scope, key)) === "1"; } catch { return false; }
}

export async function subscribe(scope, key, lang) {
  if (!pushSupported()) throw new Error("unsupported");
  const reg = await navigator.serviceWorker.register("/sw.js");
  const permission = await Notification.requestPermission();
  if (permission !== "granted") throw new Error("denied");
  const cfg = await get("/config");
  const vapid = cfg.push && cfg.push.vapid_public_key;
  if (!vapid) throw new Error("not configured");
  await navigator.serviceWorker.ready;
  const sub = (await reg.pushManager.getSubscription()) ||
    (await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: keyBytes(vapid) }));
  await post("/push/subscribe", { scope, key, subscription: sub.toJSON(), lang });
  try { localStorage.setItem(storeKey(scope, key), "1"); } catch { /* private mode */ }
}
