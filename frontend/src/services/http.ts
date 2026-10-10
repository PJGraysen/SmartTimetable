import axios from "axios";

// ---------------------------------------------------------------------
// Toast bridge ? set once from ToastProvider so axios can push toasts
// from outside React. Optional; if unset, errors are logged only.
// ---------------------------------------------------------------------
type ToastPayload = {
  type: "success" | "error" | "warning" | "info";
  title: string;
  message?: string;
  mitigation?: string;
};
let ST_TOAST_HANDLER: ((t: ToastPayload) => void) | null = null;
export function setToastHandler(fn: (t: ToastPayload) => void) {
  ST_TOAST_HANDLER = fn;
}
function toast(t: ToastPayload) {
  if (ST_TOAST_HANDLER) ST_TOAST_HANDLER(t);
  else if (t.type === "error") console.error("[http]", t.title, t.message);
}

// Same-origin requests go through the Vite dev proxy to Django.
const baseURL = "/api";

function readCookie(name: string): string | null {
  const pattern = new RegExp("(^|;\\s*)" + name + "=([^;]*)");
  const m = document.cookie.match(pattern);
  return m ? decodeURIComponent(m[2]) : null;
}

const http = axios.create({
  baseURL,
  withCredentials: true,
});

http.interceptors.request.use((config) => {
  const method = (config.method || "get").toUpperCase();
  if (["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
    const token = readCookie("csrftoken");
    if (token) {
      config.headers = config.headers || {};
      (config.headers as Record<string, string>)["X-CSRFToken"] = token;
    }
  }
  return config;
});

// Login + verification endpoints handle their own errors inline on the
// login page. Skip the global error toast for them.
const SILENT_LOGIN_URLS = [
  "/platform/auth/login/",
  "/platform/auth/verify/",
  "/platform/auth/resend-code/",
];

http.interceptors.response.use(
  (r) => r,
  (error) => {
    const resp = error?.response;
    const data = resp?.data || {};
    const status = resp?.status;

    // Login endpoints handle their own errors inline
    const requestUrl = error?.config?.url || "";
    if (SILENT_LOGIN_URLS.some((u) => requestUrl.includes(u))) {
      return Promise.reject(error);
    }

    // ---------------------------------------------------------------------
    // Build a human-readable message from any of the shapes Django/DRF
    // might return:
    //   * envelope:  { detail, hint, audit_id, code, status }
    //   * field errors: { name: ["..."], email: ["..."] }
    //   * non_field_errors: { non_field_errors: ["..."] }
    //   * plain string or list
    // ---------------------------------------------------------------------
    function extractMessage(payload: any): { text: string; fields: string[] } {
      if (!payload) return { text: "", fields: [] };
      if (typeof payload === "string") return { text: payload, fields: [] };
      if (Array.isArray(payload)) {
        return { text: payload.map(String).join(" ? "), fields: [] };
      }
      if (typeof payload === "object") {
        if (typeof payload.detail === "string") {
          return { text: payload.detail, fields: [] };
        }
        const fields: string[] = [];
        const bits: string[] = [];
        for (const [k, v] of Object.entries(payload)) {
          if (k === "hint" || k === "audit_id" || k === "code" || k === "status") continue;
          const label = k === "non_field_errors" ? "" : k + ": ";
          const value = Array.isArray(v) ? v.join(" ") : String(v);
          bits.push(label + value);
          if (k !== "non_field_errors") fields.push(k);
        }
        return { text: bits.join(" ? "), fields };
      }
      return { text: "", fields: [] };
    }

    const { text: detail, fields: errorFields } = extractMessage(data);
    const hint = data?.hint || "";
    const auditId = data?.audit_id || "";

    // Build a title/mitigation pair for the toast
    let title = `Request failed (${status ?? "network"})`;
    let mitigation = hint;
    let type: ToastPayload["type"] = "error";

    if (status === 400) {
      if (errorFields.length > 0) {
        title = "Please fix: " + errorFields.join(", ");
        mitigation = mitigation || "Correct the highlighted field(s) and try again.";
      } else {
        title = "Invalid input";
        mitigation = mitigation || "Please review the fields and try again.";
      }
    } else if (status === 401) {
      title = "Not signed in";
      mitigation = mitigation || "Please sign in again.";
    } else if (status === 403) {
      title = "Not allowed";
      mitigation = mitigation || "You do not have permission for this action.";
    } else if (status === 404) {
      title = "Not found";
      mitigation = mitigation || "The item may have been removed.";
    } else if (status === 500 || auditId) {
      title = "Server error";
      type = "error";
      mitigation = mitigation ||
        "Please try again. If it persists, share the reference with your administrator.";
    } else if (status && status >= 500) {
      title = "Server error";
      mitigation = mitigation || "Please try again in a moment.";
    }

    const msgParts: string[] = [];
    if (detail) msgParts.push(detail);
    else if (status === 400) msgParts.push("The submitted data was rejected.");
    else msgParts.push("Request failed");
    if (auditId) msgParts.push(`Reference: ${auditId}`);

    toast({
      type,
      title,
      message: msgParts.join(" ? "),
      mitigation: mitigation || undefined,
    });

    return Promise.reject(error);
  },
);

export default http;
