import DOMPurify from "dompurify";

export function sanitizeHtml(html) {
  if (typeof window === "undefined") return html || "";
  return DOMPurify.sanitize(html || "");
}
