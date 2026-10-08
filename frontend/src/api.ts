// ---------------------------------------------------------------------
// Unified HTTP client.
//
// Historically this file exported its own axios instance without CSRF
// handling, which caused "CSRF Failed: CSRF token missing." on POST.
//
// The canonical client now lives in ./services/http (CSRF header +
// response interceptor + error envelope + toast bridge). We re-export
// it here so existing imports (`import api from "../api"`) keep working
// and inherit everything automatically.
// ---------------------------------------------------------------------
export { default } from "./services/http";
