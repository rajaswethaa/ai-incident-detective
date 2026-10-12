/* ==========================================================================
   AI Incident Detective — frontend configuration
   --------------------------------------------------------------------------
   Edit the values below to point the frontend at a backend API, OR set them
   at runtime from the page's "Analysis source" panel (saved in localStorage).

   IMPORTANT: No backend API endpoint is documented in this repository yet, so
   `apiUrl` is intentionally EMPTY. Do NOT invent an endpoint or assume the
   backend exists — when your teammate provides a real URL, paste it here
   (or enter it in the UI). While `apiUrl` is empty the frontend stays in the
   clearly-labelled Demo mode.
   ========================================================================== */

window.AID_CONFIG = {
  /* Full URL of the backend analysis endpoint, e.g.
     "http://127.0.0.1:8000/analyze". Leave empty for Demo mode. */
  apiUrl: "https://ai-incident-detective.onrender.com/api/analyze/upload",

  /* How the file is sent to the backend:
     "json"      -> POST application/json  { filename, content }
     "multipart" -> POST multipart/form-data with a "file" field
     The request/response contract is documented in frontend/README.md. */
  requestFormat: "multipart",

  /* Milliseconds to wait for a backend response before aborting. */
  requestTimeoutMs: 30000
};
