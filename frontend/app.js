/* ==========================================================================
   AI Incident Detective — frontend logic (vanilla JavaScript)
   --------------------------------------------------------------------------
   Two analysis paths:
     • Demo mode   — shows clearly-labelled SAMPLE results (no AI involved).
     • Live backend — POSTs the selected file to a user-configured URL.
   No endpoint is hardcoded; the URL is empty until the user/teammate sets one.
   ========================================================================== */

(function () {
  "use strict";

  /* --------------------------------------------------------------------- */
  /* Configuration                                                          */
  /* --------------------------------------------------------------------- */

  var DEFAULTS = (window.AID_CONFIG || {});
  var STORAGE_KEYS = {
    mode: "aid.mode",
    apiUrl: "aid.apiUrl",
    requestFormat: "aid.requestFormat"
  };
  var ACCEPTED_EXTENSIONS = [".jsonl", ".log", ".json"];
  var MAX_FILE_BYTES = 5 * 1024 * 1024; // 5 MB
  var DEMO_DELAY_MS = 800;

  var settings = {
    mode: "",
    apiUrl: "",
    requestFormat: DEFAULTS.requestFormat === "multipart" ? "multipart" : "json",
    requestTimeoutMs: Number(DEFAULTS.requestTimeoutMs) || 30000
  };

  /* --------------------------------------------------------------------- */
  /* DOM references                                                         */
  /* --------------------------------------------------------------------- */

  var el = {
    modeBadge: document.getElementById("modeBadge"),
    dropZone: document.getElementById("dropZone"),
    fileInput: document.getElementById("fileInput"),
    fileName: document.getElementById("fileName"),
    analyzeButton: document.getElementById("analyzeButton"),
    clearButton: document.getElementById("clearButton"),
    loading: document.getElementById("loading"),
    loadingText: document.getElementById("loadingText"),
    errorBox: document.getElementById("errorBox"),
    errorText: document.getElementById("errorText"),
    settingsForm: document.getElementById("settingsForm"),
    apiUrl: document.getElementById("apiUrl"),
    settingsSaved: document.getElementById("settingsSaved"),
    results: document.getElementById("results"),
    demoNotice: document.getElementById("demoNotice"),
    incidentId: document.getElementById("incidentId"),
    severity: document.getElementById("severity"),
    incidentType: document.getElementById("incidentType"),
    affectedService: document.getElementById("affectedService"),
    rootCause: document.getElementById("rootCause"),
    evidenceCount: document.getElementById("evidenceCount"),
    evidenceList: document.getElementById("evidenceList"),
    stepsList: document.getElementById("stepsList"),
    resolutionBlock: document.getElementById("resolutionBlock"),
    resolution: document.getElementById("resolution")
  };

  var selectedFile = null;
  var busy = false;

  /* --------------------------------------------------------------------- */
  /* Settings persistence                                                   */
  /* --------------------------------------------------------------------- */

  function safeGet(key) {
    try {
      return window.localStorage.getItem(key);
    } catch (e) {
      return null;
    }
  }

  function safeSet(key, value) {
    try {
      window.localStorage.setItem(key, value);
    } catch (e) {
      /* storage may be unavailable (private mode); settings just won't persist */
    }
  }

  function loadSettings() {
    var storedMode = safeGet(STORAGE_KEYS.mode);
    var storedUrl = safeGet(STORAGE_KEYS.apiUrl);
    var defaultUrl = (DEFAULTS.apiUrl || "").trim();

    settings.apiUrl = (storedUrl !== null ? storedUrl : defaultUrl).trim();

    if (storedMode === "demo" || storedMode === "backend") {
      settings.mode = storedMode;
    } else {
      // Default to Demo mode unless a backend URL was configured for us.
      settings.mode = settings.apiUrl ? "backend" : "demo";
    }

    var storedFormat = safeGet(STORAGE_KEYS.requestFormat);
    if (storedFormat === "json" || storedFormat === "multipart") {
      settings.requestFormat = storedFormat;
    }
  }

  function applySettingsToForm() {
    var radios = el.settingsForm.querySelectorAll('input[name="mode"]');
    radios.forEach(function (radio) {
      radio.checked = radio.value === settings.mode;
    });
    el.apiUrl.value = settings.apiUrl;
    el.apiUrl.disabled = settings.mode !== "backend";
    updateModeBadge();
  }

  function updateModeBadge() {
    if (settings.mode === "backend") {
      el.modeBadge.textContent = "Live backend";
      el.modeBadge.classList.add("is-live");
    } else {
      el.modeBadge.textContent = "Demo mode";
      el.modeBadge.classList.remove("is-live");
    }
  }

  /* --------------------------------------------------------------------- */
  /* File selection                                                         */
  /* --------------------------------------------------------------------- */

  function extensionOf(name) {
    var dot = name.lastIndexOf(".");
    return dot === -1 ? "" : name.slice(dot).toLowerCase();
  }

  function validateFile(file) {
    if (!file) return "Please choose a file first.";
    if (ACCEPTED_EXTENSIONS.indexOf(extensionOf(file.name)) === -1) {
      return "Unsupported file type. Please upload a .jsonl, .log, or .json file.";
    }
    if (file.size === 0) {
      return "That file is empty. Pick a log file that contains at least one entry.";
    }
    if (file.size > MAX_FILE_BYTES) {
      return "That file is larger than 5 MB. Please choose a smaller log file.";
    }
    return null;
  }

  function setFile(file) {
    var problem = validateFile(file);
    if (problem) {
      showError(problem);
      clearFile();
      return;
    }
    hideError();
    selectedFile = file;
    el.fileName.textContent = "Selected: " + file.name + " (" + formatBytes(file.size) + ")";
    el.fileName.hidden = false;
    el.analyzeButton.disabled = false;
    el.clearButton.hidden = false;
  }

  function clearFile() {
    selectedFile = null;
    el.fileInput.value = "";
    el.fileName.hidden = true;
    el.fileName.textContent = "";
    el.analyzeButton.disabled = true;
    el.clearButton.hidden = true;
  }

  function formatBytes(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(2) + " MB";
  }

  /* --------------------------------------------------------------------- */
  /* Messages / UI state                                                    */
  /* --------------------------------------------------------------------- */

  function showError(message) {
    el.errorText.textContent = message;
    el.errorBox.hidden = false;
  }

  function hideError() {
    el.errorBox.hidden = true;
    el.errorText.textContent = "";
  }

  function setLoading(isLoading, text) {
    busy = isLoading;
    el.loading.hidden = !isLoading;
    if (text) el.loadingText.textContent = text;
    el.analyzeButton.disabled = isLoading || !selectedFile;
    el.analyzeButton.textContent = isLoading ? "Analyzing…" : "Analyze Incident";
  }

  /* --------------------------------------------------------------------- */
  /* Analyze                                                                */
  /* --------------------------------------------------------------------- */

  function analyze() {
    if (busy) return;
    if (!selectedFile) {
      showError("Please choose a file first.");
      return;
    }
    hideError();
    el.results.hidden = true;

    if (settings.mode === "backend") {
      if (!settings.apiUrl) {
        showError("Live backend is selected but no API URL is set. Add one in the “Analysis source” panel, or switch to Demo mode.");
        return;
      }
      runBackendAnalysis();
    } else {
      runDemoAnalysis();
    }
  }

  function runDemoAnalysis() {
    setLoading(true, "Analyzing incident… (demo mode)");
    window.setTimeout(function () {
      var report = pickSampleReport(selectedFile.name);
      setLoading(false);
      renderReport(report, { demo: true });
    }, DEMO_DELAY_MS);
  }

  function pickSampleReport(filename) {
    var name = String(filename || "").toLowerCase();
    var keys = Object.keys(window.AID_SAMPLE_REPORTS);

    var rules = [
      { test: /(database|db[_-]?fail|connection[_-]?pool|pool)/, key: "database_failure" },
      { test: /(http|500|server[_-]?error|exception[_-]?http)/, key: "http_500_error" },
      { test: /(rate|limit|throttl|429)/, key: "api_rate_limit" },
      { test: /(application|typeerror|report|aggregat)/, key: "application_exception" },
      { test: /(timeout|latency|slow)/, key: "request_timeout" },
      { test: /(auth|login|password|credential)/, key: "authentication_failure" },
      { test: /(resource|disk|memory|enospc|exhaust)/, key: "resource_exhaustion" }
    ];

    for (var i = 0; i < rules.length; i++) {
      if (rules[i].test.test(name) && keys.indexOf(rules[i].key) !== -1) {
        return window.AID_SAMPLE_REPORTS[rules[i].key];
      }
    }

    // Unknown filename: choose deterministically so the demo is reproducible.
    var order = window.AID_SAMPLE_ORDER || keys;
    var hash = 0;
    for (var j = 0; j < name.length; j++) {
      hash = (hash * 31 + name.charCodeAt(j)) >>> 0;
    }
    var chosen = order[hash % order.length];
    return window.AID_SAMPLE_REPORTS[chosen];
  }

  function runBackendAnalysis() {
    setLoading(true, "Sending file to the backend…");

    var controller = ("AbortController" in window) ? new AbortController() : null;
    var timer = null;
    if (controller) {
      timer = window.setTimeout(function () { controller.abort(); }, settings.requestTimeoutMs);
    }

    var requestOptions = { method: "POST", headers: { Accept: "application/json" } };

    if (settings.requestFormat === "multipart") {
      var form = new FormData();
      form.append("file", selectedFile, selectedFile.name);
      requestOptions.body = form; // browser sets the multipart boundary
    } else {
      requestOptions.headers["Content-Type"] = "application/json";
    }

    if (controller) requestOptions.signal = controller.signal;

    function buildBody() {
      if (settings.requestFormat === "multipart") return null;
      return selectedFile.text().then(function (content) {
        return JSON.stringify({ filename: selectedFile.name, content: content });
      });
    }

    Promise.resolve(buildBody())
      .then(function (body) {
        if (body !== null) requestOptions.body = body;
        return fetch(settings.apiUrl, requestOptions);
      })
      .then(function (response) {
        if (!response.ok) {
          throw new Error("__HTTP__" + response.status + " " + (response.statusText || ""));
        }
        return response.text();
      })
      .then(function (raw) {
        var data;
        try {
          data = JSON.parse(raw);
        } catch (e) {
          throw new Error("The backend response was not valid JSON. Check the API URL and response format.");
        }
        var report = normalizeReport(data);
        if (!report) {
          throw new Error("The backend response did not contain an incident report. Check that the endpoint returns the expected fields (documented in frontend/README.md).");
        }
        if (timer) window.clearTimeout(timer);
        setLoading(false);
        renderReport(report, { demo: false });
      })
      .catch(function (err) {
        if (timer) window.clearTimeout(timer);
        setLoading(false);
        var message = friendlyBackendError(err);
        showError(message);
      });
  }

  function friendlyBackendError(err) {
    if (err && err.name === "AbortError") {
      return "The backend did not respond within " + Math.round(settings.requestTimeoutMs / 1000) + " seconds. Check that it is running.";
    }
    if (err && typeof err.message === "string" && err.message.indexOf("__HTTP__") === 0) {
      return "The backend returned an error: HTTP " + err.message.replace("__HTTP__", "") + ". Check the API URL and that the file is valid.";
    }
    if (err && /Failed to fetch|NetworkError|Load failed/i.test(String(err.message))) {
      return "Could not reach the backend at " + settings.apiUrl + ". Make sure it is running and that the URL is correct.";
    }
    return (err && err.message) ? err.message : "Something went wrong while contacting the backend.";
  }

  /* --------------------------------------------------------------------- */
  /* Response normalisation                                                 */
  /* --------------------------------------------------------------------- */

  function normalizeReport(data) {
    if (!data) return null;

    var candidate = data;
    if (Array.isArray(data)) candidate = data[0];
    else if (data.report) candidate = data.report;
    else if (data.result) candidate = data.result;
    else if (data.data && typeof data.data === "object") candidate = data.data;

    if (!candidate || typeof candidate !== "object") return null;

    var hasIdentity = candidate.incident_type || candidate.severity || candidate.probable_root_cause;
    if (!hasIdentity) return null;

    return {
      incident_id: candidate.incident_id || "",
      incident_type: candidate.incident_type || "Unknown",
      severity: String(candidate.severity || "unknown").toLowerCase(),
      affected_service: candidate.affected_service || "Unknown",
      probable_root_cause: candidate.probable_root_cause || "Not provided.",
      evidence: Array.isArray(candidate.evidence) ? candidate.evidence : [],
      troubleshooting_steps: Array.isArray(candidate.troubleshooting_steps) ? candidate.troubleshooting_steps : [],
      expected_resolution: candidate.expected_resolution || ""
    };
  }

  /* --------------------------------------------------------------------- */
  /* Rendering                                                              */
  /* --------------------------------------------------------------------- */

  function renderReport(report, options) {
    hideError();

    // Demo notice is shown only for sample data.
    el.demoNotice.hidden = !options.demo;

    el.incidentId.textContent = report.incident_id ? "id: " + report.incident_id : "";

    var severity = ["low", "medium", "high", "critical"].indexOf(report.severity) !== -1
      ? report.severity : "unknown";
    el.severity.textContent = severity === "unknown" ? "Unknown" : capitalise(severity);
    el.severity.className = "badge badge--" + severity;

    el.incidentType.textContent = humanise(report.incident_type);
    el.affectedService.textContent = report.affected_service || "Unknown";
    el.rootCause.textContent = report.probable_root_cause || "Not provided.";

    // Evidence
    el.evidenceList.innerHTML = "";
    var evidence = report.evidence || [];
    el.evidenceCount.textContent = evidence.length + (evidence.length === 1 ? " item" : " items");
    if (evidence.length === 0) {
      el.evidenceList.appendChild(emptyNote("No supporting evidence was returned."));
    } else {
      evidence.forEach(function (item) {
        el.evidenceList.appendChild(buildEvidenceItem(item));
      });
    }

    // Troubleshooting steps
    el.stepsList.innerHTML = "";
    var steps = report.troubleshooting_steps || [];
    if (steps.length === 0) {
      el.stepsList.appendChild(emptyNote("No troubleshooting steps were returned."));
    } else {
      steps.forEach(function (step) {
        var li = document.createElement("li");
        li.textContent = String(step);
        el.stepsList.appendChild(li);
      });
    }

    // Optional expected resolution
    if (report.expected_resolution) {
      el.resolution.textContent = report.expected_resolution;
      el.resolutionBlock.hidden = false;
    } else {
      el.resolutionBlock.hidden = true;
    }

    el.results.hidden = false;
    el.results.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function buildEvidenceItem(item) {
    var li = document.createElement("li");
    li.className = "evidence-item";

    var head = document.createElement("div");
    head.className = "evidence-item__head";

    var level = String(item.level || "INFO").toLowerCase();
    var chip = document.createElement("span");
    chip.className = "level-chip level-chip--" + level;
    chip.textContent = String(item.level || "INFO").toUpperCase();
    head.appendChild(chip);

    if (item.timestamp) {
      var time = document.createElement("span");
      time.className = "evidence-item__time";
      time.textContent = item.timestamp;
      head.appendChild(time);
    }
    if (item.service) {
      var svc = document.createElement("span");
      svc.className = "evidence-item__service";
      svc.textContent = item.host ? item.service + " · " + item.host : item.service;
      head.appendChild(svc);
    }

    var message = document.createElement("p");
    message.className = "evidence-item__message";
    message.textContent = item.message || "(no message)";

    li.appendChild(head);
    li.appendChild(message);

    if (item.details && typeof item.details === "object" && Object.keys(item.details).length > 0) {
      var details = document.createElement("pre");
      details.className = "evidence-item__details";
      details.textContent = JSON.stringify(item.details, null, 2);
      li.appendChild(details);
    }

    return li;
  }

  function emptyNote(text) {
    var li = document.createElement("li");
    li.className = "evidence-item";
    li.textContent = text;
    return li;
  }

  function capitalise(text) {
    text = String(text);
    return text.charAt(0).toUpperCase() + text.slice(1);
  }

  function humanise(text) {
    text = String(text || "Unknown");
    return text.replace(/_/g, " ").replace(/\b\w/g, function (c) { return c.toUpperCase(); });
  }

  /* --------------------------------------------------------------------- */
  /* Event wiring                                                           */
  /* --------------------------------------------------------------------- */

  function init() {
    loadSettings();
    applySettingsToForm();

    // File picker
    el.dropZone.addEventListener("click", function () { el.fileInput.click(); });
    el.dropZone.addEventListener("keydown", function (event) {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        el.fileInput.click();
      }
    });
    el.fileInput.addEventListener("change", function () {
      if (el.fileInput.files && el.fileInput.files[0]) setFile(el.fileInput.files[0]);
    });

    // Drag and drop
    ["dragenter", "dragover"].forEach(function (type) {
      el.dropZone.addEventListener(type, function (event) {
        event.preventDefault();
        el.dropZone.classList.add("is-dragover");
      });
    });
    ["dragleave", "drop"].forEach(function (type) {
      el.dropZone.addEventListener(type, function (event) {
        event.preventDefault();
        el.dropZone.classList.remove("is-dragover");
      });
    });
    el.dropZone.addEventListener("drop", function (event) {
      if (event.dataTransfer && event.dataTransfer.files && event.dataTransfer.files[0]) {
        setFile(event.dataTransfer.files[0]);
      }
    });

    // Buttons
    el.analyzeButton.addEventListener("click", analyze);
    el.clearButton.addEventListener("click", function () {
      clearFile();
      hideError();
      el.results.hidden = true;
    });

    // Settings
    el.settingsForm.addEventListener("change", function (event) {
      if (event.target.name === "mode") {
        el.apiUrl.disabled = event.target.value !== "backend";
      }
    });
    el.settingsForm.addEventListener("submit", function (event) {
      event.preventDefault();
      var chosen = el.settingsForm.querySelector('input[name="mode"]:checked');
      settings.mode = chosen ? chosen.value : "demo";
      settings.apiUrl = el.apiUrl.value.trim();

      if (settings.mode === "backend" && !settings.apiUrl) {
        showError("Please enter a backend API URL before switching to Live backend.");
        return;
      }
      hideError();
      safeSet(STORAGE_KEYS.mode, settings.mode);
      safeSet(STORAGE_KEYS.apiUrl, settings.apiUrl);
      updateModeBadge();
      el.settingsSaved.hidden = false;
      window.setTimeout(function () { el.settingsSaved.hidden = true; }, 2000);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
