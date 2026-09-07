export function registerServiceWorker() {
  if (typeof window === "undefined" || process.env.NODE_ENV !== "production") return;
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => undefined);
  });
}
