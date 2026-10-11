# AI Incident Detective — Frontend

A simple, dependency-free frontend for the **AI Incident Detective** demo project.
It lets you upload an incident log, click **Analyze Incident**, and see a
structured report (severity, incident type, affected service, probable root
cause, supporting evidence, and troubleshooting steps).

Built with plain **HTML + CSS + vanilla JavaScript** — no React, no build step,
no `npm install`.

---

## 1. Files in this folder

| File | Purpose |
|------|---------|
| `index.html` | Page structure (upload panel, settings, results sections). |
| `styles.css` | All styling (clean, modern, responsive). |
| `app.js` | UI logic: file selection, validation, analysis, rendering, errors. |
| `config.js` | Default configuration (backend URL, request format, timeout). |
| `sample-data.js` | Sample results used by **Demo mode** only. |
| `README.md` | This file. |

> Nothing outside `frontend/` is modified by the frontend.

---

## 2. How to run the frontend

You can open it in two ways. A tiny local web server is recommended, because
browsers block `fetch()` calls to a backend from a `file://` page.

### Option A — Python static server (recommended)

From the **project root** (`ai-incident-detective-main/`):

```bash
python -m http.server 5173
```

Then open <http://localhost:5173/frontend/> in your browser.

### Option B — open the file directly

Double-click `frontend/index.html` (or open it in your browser). This works for
**Demo mode**. Live backend calls may be blocked by the browser's CORS policy
unless the backend allows your page origin.

There is nothing to install — it is just static files.

---

## 3. Demo mode (default)

The backend is **not connected yet**, so the frontend starts in **Demo mode**.

- Demo mode shows **sample results** taken from the project's ground-truth files
  in `../log_generation/expected_reports/`.
- Every demo result is shown behind a clear banner:
  *“Demo mode: these are sample results … not real AI analysis.”*
- Sample results are **never** presented as real AI output.

To demo it, upload any file from `../log_generation/logs/`, for example
`database_failure.jsonl` or `http_500_error.jsonl`, and click **Analyze Incident**.
Demo mode matches the filename to the closest sample incident.

---

## 4. Connecting the real backend (when it is ready)

> **Important:** this project currently documents **no backend API endpoint**, so
> the frontend does **not** assume one. The backend is being developed separately.

When your teammate gives you a URL, you have two ways to set it:

1. **In the UI (no code change):** in the *“Analysis source”* panel choose
   **Live backend**, paste the URL (e.g. `http://127.0.0.1:8000/analyze`), and
   click **Save settings**. It is stored only in your browser (`localStorage`).
2. **In `config.js`:** set `apiUrl` to the endpoint URL. This becomes the default
   for anyone opening the page.

While `apiUrl` is empty, the page stays safely in Demo mode.

### Request format the frontend sends

The frontend `POST`s to the configured URL. The format is chosen by
`requestFormat` in `config.js` (`"json"` by default):

**`"json"`:**

```http
POST <apiUrl>
Content-Type: application/json

{
  "filename": "database_failure.jsonl",
  "content": "<the raw text of the uploaded file>"
}
```

**`"multipart"`:**

```
POST <apiUrl>
Content-Type: multipart/form-data
field name: file
```

### Response format the frontend expects

A single JSON object with these fields (the same shape as
`../log_generation/expected_reports/*.json`):

```json
{
  "incident_id": "database_failure",
  "incident_type": "database_connection_failure",
  "severity": "high",
  "affected_service": "order-service",
  "probable_root_cause": "…",
  "evidence": [
    {
      "timestamp": "2026-10-11T06:05:12.759Z",
      "level": "WARNING",
      "service": "order-service",
      "host": "ord-svc-01",
      "message": "Connection pool nearing exhaustion",
      "details": { "pool_active": 50, "pool_max": 50 }
    }
  ],
  "troubleshooting_steps": ["…", "…"],
  "expected_resolution": "…"
}
```

The frontend also accepts the report wrapped in `{ "report": { … } }` or
`{ "result": { … } }`, or returned as a one-element array.

If your teammate's endpoint shape differs, either adapt the backend or update
`normalizeReport()` in `app.js` (it converts the response into the fields above).

---

## 5. Configuring the demo (optional)

Open `config.js`:

```js
window.AID_CONFIG = {
  apiUrl: "",              // leave empty for Demo mode
  requestFormat: "json",   // "json" or "multipart"
  requestTimeoutMs: 30000  // abort a slow backend after 30s
};
```

---

## 6. Testing checklist

| Test | Expected result |
|------|-----------------|
| Open `http://localhost:5173/frontend/` | Dashboard titled **AI Incident Detective** with a badge showing **Demo mode**. |
| Upload `../log_generation/logs/database_failure.jsonl`, click **Analyze Incident** | Spinner appears, then a **high** severity report with evidence and steps, plus a Demo-mode banner. |
| Upload a `.txt` or an empty file | Friendly error message; the analyze button stays disabled. |
| Try to click **Analyze Incident** with no file | “Please choose a file first.” |
| Switch to **Live backend** with an empty URL and save | Friendly validation message. |
| Save a backend URL, then switch back | URL persists after reload (stored in `localStorage`). |
| Resize the window to mobile width | Layout stacks into a single column cleanly. |

---

## 7. Notes for reviewers

- The frontend reads files locally in the browser; it only sends data to a
  backend when **Live backend** mode is selected and a URL is configured.
- No external libraries, fonts, or CDNs are used — it works fully offline in
  Demo mode.
