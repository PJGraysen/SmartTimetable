import axios from "axios";

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

export default http;
