const API_BASE_URL = window.APP_CONFIG?.apiEndpoint;

if (!API_BASE_URL) {
  throw new Error("Missing API endpoint configuration");
}

const page = document.body.dataset.page;

const analyzeButton = document.getElementById("analyzeButton");
const uploadButton = document.getElementById("uploadButton");
const analyzeButtonTooltip = document.getElementById("analyzeButtonTooltip");
const uploadButtonTooltip = document.getElementById("uploadButtonTooltip");
const refreshHistoryButton = document.getElementById("refreshHistoryButton");
const deleteAllAnalysesButton = document.getElementById("deleteAllAnalysesButton");

const matchJobButton = document.getElementById("matchJobButton");
const matchJobButtonTooltip = document.getElementById("matchJobButtonTooltip");
const refreshJobMatchesButton = document.getElementById("refreshJobMatchesButton");
const deleteAllJobMatchesButton = document.getElementById("deleteAllJobMatchesButton");

const textTab = document.getElementById("textTab");
const pdfTab = document.getElementById("pdfTab");
const textPanel = document.getElementById("textPanel");
const pdfPanel = document.getElementById("pdfPanel");

const providerSelect = document.getElementById("analysisProvider");
const textarea = document.getElementById("resumeText");
const fileInput = document.getElementById("resumeFile");
const result = document.getElementById("result");
const history = document.getElementById("history");

const resumeAnalysisSelect = document.getElementById("resumeAnalysisSelect");
const jobResumeList = document.getElementById("jobResumeList");
const jobResumeLoading = document.getElementById("jobResumeLoading");
const jobResumeEmpty = document.getElementById("jobResumeEmpty");
const jobResumeError = document.getElementById("jobResumeError");
const jobName = document.getElementById("jobName");
const jobUrl = document.getElementById("jobUrl");
const jobDescriptionText = document.getElementById("jobDescriptionText");
const jobMatches = document.getElementById("jobMatches");

const resumeName = document.getElementById("resumeName");
const resumeTargetCareerList = document.getElementById("resumeTargetCareerList");
const resumeTargetCareerLoading = document.getElementById("resumeTargetCareerLoading");
const resumeTargetCareerEmpty = document.getElementById("resumeTargetCareerEmpty");
const resumeTargetCareerError = document.getElementById("resumeTargetCareerError");
const resumeAnalysisInputs = document.getElementById("resumeAnalysisInputs");

const resumeSummary = document.getElementById("resumeSummary");
const resumeSearchInput = document.getElementById("resumeSearchInput");
const resumeSortSelect = document.getElementById("resumeSortSelect");

const jobMatchSummary = document.getElementById("jobMatchSummary");
const jobSearchInput = document.getElementById("jobSearchInput");
const jobSortSelect = document.getElementById("jobSortSelect");

const urlParams = new URLSearchParams(window.location.search);
const deepLinkAnalysisId = urlParams.get("analysisId");
const deepLinkMatchId = urlParams.get("matchId");

const accordionConfigs = {
  "resume-analysis": [
    "analyzeResumeCard",
    "resumeResultCard",
    "analysisHistoryCard"
  ],
  "job-matching": [
    "matchJobCard",
    "jobResultCard",
    "jobHistoryCard"
  ]
};

let cachedResumeAnalyses = [];
let cachedJobMatches = [];
let resumeTargetCareers = [];
let selectedResumeTargetCareerId = "";
let selectedJobResumeAnalysisId = "";

const ANALYSIS_POLL_TIMEOUT_MS = 5 * 60 * 1000;
const ANALYSIS_POLL_DELAYS_MS = [0, 2000, 4000, 6000, 10000];
const ANALYSIS_POLL_INTERVAL_MS = 10000;
let activeAnalysisPollToken = 0;
let activeAnalysisId = null;
let analysisTransitionTimer = null;

const JOB_MATCH_POLL_TIMEOUT_MS = 5 * 60 * 1000;
const JOB_MATCH_POLL_DELAYS_MS = [0, 2000, 4000, 6000, 10000];
const JOB_MATCH_POLL_INTERVAL_MS = 10000;
let activeJobMatchPollToken = 0;
let activeJobMatchId = null;
let jobMatchTransitionTimer = null;

const ANALYSIS_STATUS_PRESENTATION = {
  queued_pending_dispatch: {
    label: "Preparing your resume analysis…",
    historyLabel: "Preparing",
    category: "processing"
  },
  queued: {
    label: "Your resume is waiting to be analyzed…",
    historyLabel: "Waiting",
    category: "processing"
  },
  worker_processing: {
    label: "Analyzing your resume…",
    historyLabel: "Analyzing",
    category: "processing"
  },
  processing: {
    label: "Analyzing your resume…",
    historyLabel: "Analyzing",
    category: "processing"
  },
  failed_retryable: {
    label: "Analysis is taking longer than expected. We’re retrying…",
    historyLabel: "Retrying",
    category: "processing"
  },
  result_ready_pending_child_dispatch: {
    label: "Preparing your recommendations…",
    historyLabel: "Finishing",
    category: "processing"
  },
  completed: {
    label: "Resume analysis complete",
    historyLabel: "Complete",
    category: "completed"
  },
  failed_permanent: {
    label: "We couldn’t analyze this resume. Please try again.",
    historyLabel: "Needs attention",
    category: "failed"
  },
  failed_retry_exhausted: {
    label: "We couldn’t analyze this resume after several attempts. Please try again.",
    historyLabel: "Needs attention",
    category: "failed"
  },
  failed: {
    label: "We couldn’t analyze this resume. Please try again.",
    historyLabel: "Needs attention",
    category: "failed"
  }
};

const JOB_MATCH_STATUS_PRESENTATION = {
  queued_pending_dispatch: {
    label: "Preparing your job match…",
    historyLabel: "Preparing",
    category: "processing"
  },
  queued: {
    label: "Your job match is waiting to begin…",
    historyLabel: "Waiting",
    category: "processing"
  },
  worker_processing: {
    label: "Comparing your resume with the job…",
    historyLabel: "Matching",
    category: "processing"
  },
  processing: {
    label: "Comparing your resume with the job…",
    historyLabel: "Matching",
    category: "processing"
  },
  failed_retryable: {
    label: "Your job match is taking longer than expected. We’re retrying…",
    historyLabel: "Retrying",
    category: "processing"
  },
  result_ready_pending_child_dispatch: {
    label: "Preparing your match recommendations…",
    historyLabel: "Finishing",
    category: "processing"
  },
  completed: {
    label: "Job match complete",
    historyLabel: "Complete",
    category: "completed"
  },
  failed_permanent: {
    label: "We couldn’t complete this job match. Please try again.",
    historyLabel: "Needs attention",
    category: "failed"
  },
  failed_retry_exhausted: {
    label: "We couldn’t complete this job match after several attempts. Please try again.",
    historyLabel: "Needs attention",
    category: "failed"
  },
  failed: {
    label: "We couldn’t complete this job match. Please try again.",
    historyLabel: "Needs attention",
    category: "failed"
  }
};


function normalizeWorkflowStatus(status) {
  return String(status || "unknown")
    .trim()
    .toLowerCase()
    .replaceAll("-", "_")
    .replaceAll(" ", "_");
}

function analysisStatusPresentation(status) {
  const normalized = normalizeWorkflowStatus(status);
  return ANALYSIS_STATUS_PRESENTATION[normalized] || {
    label: "Processing your resume analysis…",
    historyLabel: "In progress",
    category: "processing"
  };
}

function isAnalysisInProgress(status) {
  return analysisStatusPresentation(status).category === "processing";
}

function isAnalysisCompleted(status) {
  return analysisStatusPresentation(status).category === "completed";
}

function isAnalysisFailed(status) {
  return analysisStatusPresentation(status).category === "failed";
}

function jobMatchStatusPresentation(status) {
  const normalized = normalizeWorkflowStatus(status);
  return JOB_MATCH_STATUS_PRESENTATION[normalized] || {
    label: "Processing your job match…",
    historyLabel: "In progress",
    category: "processing"
  };
}

function isJobMatchInProgress(status) {
  return jobMatchStatusPresentation(status).category === "processing";
}

function isJobMatchCompleted(status) {
  return jobMatchStatusPresentation(status).category === "completed";
}

function isJobMatchFailed(status) {
  return jobMatchStatusPresentation(status).category === "failed";
}

function wait(delayMs) {
  return new Promise(resolve => setTimeout(resolve, delayMs));
}

function stopAnalysisPolling() {
  activeAnalysisPollToken += 1;
  activeAnalysisId = null;
}

function transitionToAnalysisResult(delayMs = 2500) {
  if (analysisTransitionTimer) {
    clearTimeout(analysisTransitionTimer);
  }

  setAccordionOpen("resumeResultCard", true);

  analysisTransitionTimer = setTimeout(() => {
    setAccordionOpen("analyzeResumeCard", false);
    focusAccordionCard("resumeResultCard", true);
    analysisTransitionTimer = null;
  }, delayMs);
}

function renderAnalysisProgress(status, message) {
  if (!result) {
    return;
  }

  const presentation = analysisStatusPresentation(status);
  const detail = message || "This normally takes less than a minute. We’ll update this page automatically.";

  result.innerHTML = `
    <div class="analysis-progress" role="status" aria-live="polite" aria-atomic="true">
      <div class="progress-spinner" aria-hidden="true"></div>
      <div>
        <h3>${escapeHtml(presentation.label)}</h3>
        <p>${escapeHtml(detail)}</p>
      </div>
    </div>
  `;
}

function stopJobMatchPolling() {
  activeJobMatchPollToken += 1;
  activeJobMatchId = null;
}

function transitionToJobMatchResult(delayMs = 2500) {
  if (jobMatchTransitionTimer) {
    clearTimeout(jobMatchTransitionTimer);
  }

  setAccordionOpen("jobResultCard", true);

  jobMatchTransitionTimer = setTimeout(() => {
    setAccordionOpen("matchJobCard", false);
    focusAccordionCard("jobResultCard", true);
    jobMatchTransitionTimer = null;
  }, delayMs);
}

function renderJobMatchProgress(status, message) {
  if (!result) {
    return;
  }

  const presentation = jobMatchStatusPresentation(status);
  const detail = message || "This normally takes less than a minute. We’ll update this page automatically.";

  result.innerHTML = `
    <div class="analysis-progress" role="status" aria-live="polite" aria-atomic="true">
      <div class="progress-spinner" aria-hidden="true"></div>
      <div>
        <h3>${escapeHtml(presentation.label)}</h3>
        <p>${escapeHtml(detail)}</p>
      </div>
    </div>
  `;
}

const protectedPages = ["resume-analysis", "job-matching"];

if (protectedPages.includes(page) && !requireAuth()) {
  throw new Error("Authentication required");
}

function accordionKey(id) {
  return `accordion:${page}:${id}`;
}

function hasAccordionSessionState() {
  return (accordionConfigs[page] || []).some(id =>
    sessionStorage.getItem(accordionKey(id)) !== null
  );
}

function setAccordionOpen(id, isOpen) {
  const element = document.getElementById(id);

  if (!element) {
    return;
  }

  element.open = isOpen;
  sessionStorage.setItem(accordionKey(id), String(isOpen));
}

function setupAccordionPersistence() {
  const ids = accordionConfigs[page] || [];

  ids.forEach(id => {
    const element = document.getElementById(id);

    if (!element) {
      return;
    }

    const savedValue = sessionStorage.getItem(accordionKey(id));

    if (savedValue !== null) {
      element.open = savedValue === "true";
    }

    element.addEventListener("toggle", () => {
      sessionStorage.setItem(accordionKey(id), String(element.open));
    });
  });
}

function openResumeDetailView() {
  setAccordionOpen("analyzeResumeCard", false);
  setAccordionOpen("resumeResultCard", true);
  setAccordionOpen("analysisHistoryCard", true);
}

function openJobDetailView() {
  setAccordionOpen("matchJobCard", false);
  setAccordionOpen("jobResultCard", true);
  setAccordionOpen("jobHistoryCard", true);
}

function applyDefaultResumeAccordionState() {
  if (hasAccordionSessionState() || deepLinkAnalysisId) {
    return;
  }

  const hasResumes = cachedResumeAnalyses.length > 0;

  setAccordionOpen("analyzeResumeCard", !hasResumes);
  setAccordionOpen("resumeResultCard", false);
  setAccordionOpen("analysisHistoryCard", hasResumes);
}

function applyDefaultJobAccordionState() {
  if (hasAccordionSessionState() || deepLinkMatchId) {
    return;
  }

  const hasMatches = cachedJobMatches.length > 0;

  setAccordionOpen("matchJobCard", !hasMatches);
  setAccordionOpen("jobResultCard", false);
  setAccordionOpen("jobHistoryCard", hasMatches);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}


function targetCareerVersionLabel(career) {
  return `v${Number(career?.version || 1)}`;
}

function targetCareerLastUpdated(career) {
  return formatEastern(career?.updatedAt || career?.createdAt);
}

function analysisTargetCareer(data) {
  return data?.targetCareer || {};
}

function analysisContextPanelMarkup(data, orientation = "horizontal") {
  const career = analysisTargetCareer(data);
  const roleTitle = career.roleTitle || data?.targetRoleTitle || "Target Career unavailable";
  const version = targetCareerVersionLabel(career);
  const name = data?.resumeName || "Untitled Resume";
  const fileName = data?.fileName || "";

  return `
    <div class="analysis-context-panels ${escapeHtml(orientation)}">
      <div class="analysis-context-panel">
        <span class="analysis-context-label">Target Career</span>
        <strong>${escapeHtml(roleTitle)} <span class="analysis-context-version">${escapeHtml(version)}</span></strong>
      </div>
      <div class="analysis-context-panel">
        <span class="analysis-context-label">Resume</span>
        <strong>${escapeHtml(name)}</strong>
        ${fileName ? `<span class="analysis-context-file">${escapeHtml(fileName)}</span>` : ""}
      </div>
    </div>
  `;
}

function analysisPreviewMarkup(data, compact = false) {
  if (data?.documentBucket && data?.documentKey && data?.analysisId) {
    return `<div class="pdf-thumbnail${compact ? " compact" : ""}" data-pdf-analysis-id="${escapeHtml(data.analysisId)}"><div class="pdf-thumbnail-loading">Loading PDF preview…</div></div>`;
  }

  const preview = data?.resumeText
    ? escapeHtml(data.resumeText.slice(0, compact ? 800 : 2000))
    : "No resume text stored.";
  return `<div class="resume-preview${compact ? " small-preview" : ""}">${preview}</div>`;
}

function atsScoreToneClass(score) {
  const numericScore = Number(score) || 0;
  if (numericScore >= 80) {
    return "score-good";
  }
  if (numericScore >= 70) {
    return "score-warning";
  }
  return "score-poor";
}

function renderAnalysis(data) {
  const status = normalizeWorkflowStatus(data.status);

  if (isAnalysisInProgress(status)) {
    renderAnalysisProgress(status);
    return;
  }

  if (isAnalysisFailed(status)) {
    const presentation = analysisStatusPresentation(status);
    result.innerHTML = `
      <div class="status-banner status-error" role="alert">
        <h3>${escapeHtml(presentation.label)}</h3>
        <p>${escapeHtml(data.errorMessage || data.message || "Please submit the resume again. If the problem continues, try another PDF.")}</p>
      </div>
    `;
    return;
  }

  const strengths = (data.strengths || [])
    .map(item => `<li>${escapeHtml(item)}</li>`)
    .join("");

  const recommendations = (data.recommendations || [])
    .map(item => `<li>${escapeHtml(item)}</li>`)
    .join("");

  const score = data.score || data.overallScore || 0;

  result.innerHTML = `
    <div class="analysis-result-header-grid">
      <div class="analysis-score-panel">
        <span class="analysis-context-label">ATS Score</span>
        <div class="score-circle ${atsScoreToneClass(score)}" aria-label="ATS score ${escapeHtml(score)}">${score}</div>
      </div>
      ${analysisContextPanelMarkup(data, "vertical")}
      <div class="metrics analysis-result-metrics">
        <span class="metric">Created: ${escapeHtml(formatEastern(data.createdAt))}</span>
        <span class="metric">Model: ${escapeHtml(data.model || "N/A")}</span>
        <span class="metric">Source: ${escapeHtml(data.sourceType || "text")}</span>
        <span class="metric">Provider: ${escapeHtml(data.provider || "rule-based")}</span>
        <span class="metric">Version: ${escapeHtml(data.analysisVersion || "unknown")}</span>
        <span class="metric">Words: ${escapeHtml(data.wordCount || 0)}</span>
        <span class="metric">Duration: ${escapeHtml(data.analysisDurationMs || 0)} ms</span>
      </div>
    </div>

    <section class="result-section-panel" aria-labelledby="roleSpecificScoresHeading">
      <h3 id="roleSpecificScoresHeading">Role-Specific Scores</h3>
      ${renderDynamicScores(data.dynamicScores)}
    </section>

    <h3>Role Fit Summary</h3>
    <p>${escapeHtml(data.roleFitSummary || "")}</p>

    <h3>Role-Specific Gaps</h3>
    <ul>${listToHtml(data.roleSpecificGaps || [])}</ul>

    <h3>Executive Summary</h3>
    <p>${escapeHtml(data.executiveSummary || "No executive summary available.")}</p>

    <div class="result-grid">
      <div class="result-box">
        <h3>Strengths</h3>
        <ul>${strengths}</ul>
      </div>

      <div class="result-box">
        <h3>Recommendations</h3>
        <ul>${recommendations}</ul>
      </div>
    </div>

    <section class="result-section-panel result-preview-panel" aria-labelledby="resumePreviewHeading">
      <h3 id="resumePreviewHeading">${data.documentBucket && data.documentKey ? "Resume PDF Preview" : "Resume Text Preview"}</h3>
      ${analysisPreviewMarkup(data)}
    </section>
  `;

  hydrateResumePdfPreviews();

  const heading = result.querySelector("h3");
  if (heading) {
    heading.tabIndex = -1;
    heading.focus({ preventScroll: true });
  }
}

function selectedResumeTargetCareer() {
  return resumeTargetCareers.find(
    (career) => career.targetCareerId === selectedResumeTargetCareerId,
  );
}

function resumeAnalysisRequirementMessage(mode) {
  const missing = [];

  if (!selectedResumeTargetCareer()) missing.push("choose a Target Career");
  if (!resumeName?.value.trim()) missing.push("specify a Resume name");
  if (mode === "text" && !textarea?.value.trim()) missing.push("paste resume text");
  if (mode === "pdf" && !fileInput?.files?.length) missing.push("upload a PDF");

  if (missing.length === 0) return "Ready to analyze your resume.";
  return `To enable this button: ${missing.join(", ")}.`;
}

function updateResumeAnalysisAvailability() {
  const hasCareers = resumeTargetCareers.length > 0;
  const textMessage = resumeAnalysisRequirementMessage("text");
  const pdfMessage = resumeAnalysisRequirementMessage("pdf");
  const textReady = textMessage === "Ready to analyze your resume.";
  const pdfReady = pdfMessage === "Ready to analyze your resume.";

  resumeAnalysisInputs?.classList.toggle("hidden", !hasCareers);
  if (analyzeButton) analyzeButton.disabled = !textReady;
  if (uploadButton) uploadButton.disabled = !pdfReady;

  if (analyzeButtonTooltip) {
    analyzeButtonTooltip.dataset.tooltip = textReady ? "" : textMessage;
    analyzeButtonTooltip.setAttribute("aria-label", textMessage);
  }
  if (uploadButtonTooltip) {
    uploadButtonTooltip.dataset.tooltip = pdfReady ? "" : pdfMessage;
    uploadButtonTooltip.setAttribute("aria-label", pdfMessage);
  }
}

function renderResumeTargetCareers() {
  if (!resumeTargetCareerList) return;

  resumeTargetCareerList.innerHTML = "";
  resumeTargetCareerEmpty?.classList.toggle("hidden", resumeTargetCareers.length !== 0);

  resumeTargetCareers.forEach((career) => {
    const label = document.createElement("label");
    label.className = "resume-target-career-option";
    if (career.targetCareerId === selectedResumeTargetCareerId) {
      label.classList.add("selected");
    }

    label.innerHTML = `
      <input
        type="radio"
        name="resumeTargetCareer"
        value="${escapeHtml(career.targetCareerId)}"
        ${career.targetCareerId === selectedResumeTargetCareerId ? "checked" : ""}
      />
      <span class="resume-target-career-copy">
        <span class="resume-target-career-title-row">
          <strong>${escapeHtml(career.roleTitle || "Untitled Target Career")}</strong>
          <span class="version-badge">${escapeHtml(targetCareerVersionLabel(career))}</span>
        </span>
        <span>${escapeHtml([career.industry, career.seniorityLevel].filter(Boolean).join(" · ") || "Career details not specified")}</span>
        <span class="resume-target-career-updated"><em>Last Updated</em> ${escapeHtml(targetCareerLastUpdated(career))}</span>
      </span>
    `;

    label.querySelector("input").addEventListener("change", (event) => {
      selectedResumeTargetCareerId = event.target.value;
      renderResumeTargetCareers();
      resumeTargetCareerError?.classList.add("hidden");
    });

    resumeTargetCareerList.appendChild(label);
  });

  updateResumeAnalysisAvailability();
}

async function loadResumeTargetCareers() {
  if (!resumeTargetCareerList) return;

  resumeTargetCareerLoading?.classList.remove("hidden");
  resumeTargetCareerError?.classList.add("hidden");

  try {
    const response = await fetch(`${API_BASE_URL}/target-careers`, {
      headers: await authHeaders(),
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data?.error?.message || data?.error || "Could not load Target Careers");
    }

    resumeTargetCareers = Array.isArray(data.targetCareers) ? data.targetCareers : [];

    if (resumeTargetCareers.length === 1) {
      selectedResumeTargetCareerId = resumeTargetCareers[0].targetCareerId;
    } else if (!resumeTargetCareers.some((career) => career.targetCareerId === selectedResumeTargetCareerId)) {
      selectedResumeTargetCareerId = "";
    }

    renderResumeTargetCareers();
  } catch (error) {
    resumeTargetCareers = [];
    selectedResumeTargetCareerId = "";
    renderResumeTargetCareers();
    if (resumeTargetCareerError) {
      resumeTargetCareerError.textContent = `Could not load Target Careers: ${error.message}`;
      resumeTargetCareerError.classList.remove("hidden");
    }
  } finally {
    resumeTargetCareerLoading?.classList.add("hidden");
  }
}

function requireSelectedResumeTargetCareer() {
  const career = selectedResumeTargetCareer();
  if (career) return career;

  if (resumeTargetCareerError) {
    resumeTargetCareerError.textContent = "Choose a Target Career before analyzing your resume.";
    resumeTargetCareerError.classList.remove("hidden");
    resumeTargetCareerError.scrollIntoView({ behavior: "smooth", block: "center" });
  }
  return null;
}

async function analyzeTextResume() {
  const resumeTextValue = textarea.value.trim();

  if (!resumeTextValue) {
    result.textContent = "Please enter resume text.";
    return;
  }

  const targetCareer = requireSelectedResumeTargetCareer();
  if (!targetCareer) return;

  /*
   * Generate once for this user action.
   * Any retry added inside this function must reuse this value.
   */
  const idempotencyKey = crypto.randomUUID();

  setButtonLoading(
    analyzeButton,
    "Analyzing...",
  );

  result.textContent = "Analyzing resume text...";
  focusAccordionCard("resumeResultCard");

  try {
    const headers = await jsonHeaders();

    headers["Idempotency-Key"] =
      idempotencyKey;

    const response = await fetch(
      `${API_BASE_URL}/analyze-resume`,
      {
        method: "POST",
        headers,
        body: JSON.stringify({
          resumeName:
            resumeName?.value.trim()
            || "Untitled Resume",
          resumeText: resumeTextValue,
          analysisProvider: selectedProvider(),
          targetCareerId: targetCareer.targetCareerId,
        }),
      },
    );

    const data = await response.json();

    if (!response.ok) {
      throw new Error(
        data?.error?.message
        || data?.error
        || "Text analysis failed",
      );
    }

    renderAnalysis(data);

    setAccordionOpen(
      "resumeResultCard",
      true,
    );

    await loadHistory();

    setButtonSaved(
      analyzeButton,
      "Complete ✓",
    );
  } catch (error) {
    result.textContent =
      `Error: ${error.message}`;

    resetButton(analyzeButton);
  }
}

async function uploadPdfResume() {
  const file = fileInput.files[0];

  if (!file) {
    result.textContent =
      "Choose a PDF file first.";
    return;
  }

  if (file.type !== "application/pdf") {
    result.textContent =
      "Only PDF files are supported.";
    return;
  }

  const targetCareer = requireSelectedResumeTargetCareer();
  if (!targetCareer) return;

  /*
   * These are two separate logical operations and must use
   * different idempotency keys.
   */
  const uploadUrlIdempotencyKey =
    crypto.randomUUID();

  const analysisIdempotencyKey =
    crypto.randomUUID();

  setButtonLoading(
    uploadButton,
    "Uploading...",
  );

  stopAnalysisPolling();
  setAccordionOpen("resumeResultCard", true);
  renderAnalysisProgress("queued_pending_dispatch", "Uploading your PDF securely…");

  try {
    const uploadHeaders = await jsonHeaders();

    uploadHeaders["Idempotency-Key"] =
      uploadUrlIdempotencyKey;

    const uploadUrlResponse = await fetch(
      `${API_BASE_URL}/resume-upload-url`,
      {
        method: "POST",
        headers: uploadHeaders,
        body: JSON.stringify({
          fileName: file.name,
          contentType: file.type,
        }),
      },
    );

    const uploadData =
      await uploadUrlResponse.json();

    if (!uploadUrlResponse.ok) {
      throw new Error(
        uploadData?.error?.message
        || uploadData?.error
        || "Could not create upload URL",
      );
    }

    renderAnalysisProgress("queued_pending_dispatch", "Uploading your PDF securely…");

    const uploadResponse = await fetch(
      uploadData.uploadUrl,
      {
        method: "PUT",
        headers: {
          "Content-Type": file.type,
        },
        body: file,
      },
    );

    if (!uploadResponse.ok) {
      throw new Error("PDF upload failed");
    }

    renderAnalysisProgress(
      "queued_pending_dispatch",
      "Your PDF is uploaded. We’re preparing the analysis…",
    );

    const analysisHeaders =
      await jsonHeaders();

    analysisHeaders["Idempotency-Key"] =
      analysisIdempotencyKey;

    const analysisResponse = await fetch(
      `${API_BASE_URL}/analyze-uploaded-resume`,
      {
        method: "POST",
        headers: analysisHeaders,
        body: JSON.stringify({
          resumeName:
            resumeName?.value.trim()
            || uploadData.fileName
            || "Untitled Resume",
          documentBucket:
            uploadData.documentBucket,
          documentKey:
            uploadData.documentKey,
          fileName:
            uploadData.fileName,
          analysisProvider:
            selectedProvider(),
          targetCareerId:
            targetCareer.targetCareerId,
        }),
      },
    );

    const analysisData =
      await analysisResponse.json();

    if (!analysisResponse.ok) {
      throw new Error(
        analysisData?.error?.message
        || analysisData?.error
        || "PDF analysis save failed",
      );
    }

    renderAnalysis(analysisData);
    transitionToAnalysisResult();
    await loadHistory({ resumeActiveAnalysis: false });

    if (analysisData.analysisId && isAnalysisInProgress(analysisData.status)) {
      void pollAnalysisUntilComplete(analysisData.analysisId);
    }

    setButtonSaved(
      uploadButton,
      "Submitted ✓",
    );
  } catch (error) {
    result.textContent =
      `Error: ${error.message}`;

    resetButton(uploadButton);
  }
}

async function loadHistory({ resumeActiveAnalysis = true } = {}) {
  if (!history && !resumeAnalysisSelect && !jobResumeList) {
    return;
  }

  if (history && cachedResumeAnalyses.length === 0) {
    history.textContent = "Loading history...";
  }

  try {
    const response = await fetch(`${API_BASE_URL}/analyses`, {
      headers: await authHeaders()
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Could not load history");
    }

    const analyses = data.analyses || [];

    cachedResumeAnalyses = analyses.filter(item =>
      item.status &&
      item.analysisId &&
      !item.matchId &&
      item.sourceType
    );

    populateResumeAnalysisSelect(cachedResumeAnalyses);
    renderJobResumeCards(cachedResumeAnalyses);

    if (history) {
      renderResumeHistory();
    }

    applyDefaultResumeAccordionState();

    if (deepLinkAnalysisId) {
      openResumeDetailView();
      await loadAnalysisDetail(deepLinkAnalysisId);
      window.history.replaceState({}, document.title, window.location.pathname);
      return;
    }

    if (resumeActiveAnalysis) {
      const activeAnalysis = cachedResumeAnalyses.find(item =>
        item.analysisId && isAnalysisInProgress(item.status)
      );

      if (activeAnalysis) {
        setAccordionOpen("analyzeResumeCard", false);
        setAccordionOpen("resumeResultCard", true);
        renderAnalysis(activeAnalysis);
        void pollAnalysisUntilComplete(activeAnalysis.analysisId);
      }
    }
  } catch (error) {
    if (history) {
      history.textContent = `Error: ${error.message}`;
    }
    if (jobResumeList) {
      jobResumeLoading?.classList.add("hidden");
      jobResumeEmpty?.classList.add("hidden");
      jobResumeError?.classList.remove("hidden");
      jobResumeError.textContent = `Could not load resumes: ${error.message}`;
    }
  }
}

async function pollAnalysisUntilComplete(analysisId) {
  if (!analysisId) {
    return;
  }

  if (activeAnalysisId === analysisId) {
    return;
  }

  stopAnalysisPolling();
  activeAnalysisId = analysisId;
  const pollToken = activeAnalysisPollToken;
  const startedAt = Date.now();
  let attempt = 0;

  while (
    pollToken === activeAnalysisPollToken
    && activeAnalysisId === analysisId
    && Date.now() - startedAt < ANALYSIS_POLL_TIMEOUT_MS
  ) {
    const delayMs = attempt < ANALYSIS_POLL_DELAYS_MS.length
      ? ANALYSIS_POLL_DELAYS_MS[attempt]
      : ANALYSIS_POLL_INTERVAL_MS;

    if (delayMs > 0) {
      await wait(delayMs);
    }

    if (pollToken !== activeAnalysisPollToken || activeAnalysisId !== analysisId) {
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/analysis/${encodeURIComponent(analysisId)}`, {
        headers: await authHeaders()
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data?.error?.message || data.error || "Could not refresh analysis detail");
      }

      renderAnalysis(data);
      await loadHistory({ resumeActiveAnalysis: false });

      if (!isAnalysisInProgress(data.status)) {
        stopAnalysisPolling();
        return;
      }
    } catch (error) {
      console.warn("Could not refresh resume analysis:", error);
      renderAnalysisProgress(
        "failed_retryable",
        "We couldn’t refresh the status just now. We’ll try again automatically.",
      );
    }

    attempt += 1;
  }

  if (pollToken === activeAnalysisPollToken && activeAnalysisId === analysisId) {
    stopAnalysisPolling();
    result.innerHTML = `
      <div class="status-banner status-warning" role="status" aria-live="polite">
        <h3>This analysis is taking longer than usual.</h3>
        <p>You may leave this page and check Analysis History later. Use Refresh History to check again.</p>
      </div>
    `;
    await loadHistory({ resumeActiveAnalysis: false });
  }
}

async function pollJobMatchUntilComplete(matchId) {
  if (!matchId) {
    return;
  }

  if (activeJobMatchId === matchId) {
    return;
  }

  stopJobMatchPolling();
  activeJobMatchId = matchId;
  const pollToken = activeJobMatchPollToken;
  const startedAt = Date.now();
  let attempt = 0;

  while (
    pollToken === activeJobMatchPollToken
    && activeJobMatchId === matchId
    && Date.now() - startedAt < JOB_MATCH_POLL_TIMEOUT_MS
  ) {
    const delayMs = attempt < JOB_MATCH_POLL_DELAYS_MS.length
      ? JOB_MATCH_POLL_DELAYS_MS[attempt]
      : JOB_MATCH_POLL_INTERVAL_MS;

    if (delayMs > 0) {
      await wait(delayMs);
    }

    if (pollToken !== activeJobMatchPollToken || activeJobMatchId !== matchId) {
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/job-match/${encodeURIComponent(matchId)}`, {
        headers: await authHeaders()
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data?.error?.message || data.error || "Could not refresh job match detail");
      }

      renderJobMatch(data);
      await loadJobMatches({ resumeActiveMatch: false });

      if (!isJobMatchInProgress(data.status)) {
        stopJobMatchPolling();

        if (isJobMatchCompleted(data.status)) {
          const tailoring = await fetchTailoringForMatch(matchId);
          const interviewPrep = await fetchInterviewPrepForMatch(matchId);
          renderJobMatch(data, tailoring, interviewPrep);
          focusAccordionCard("jobResultCard", true);
          await loadJobMatches({ resumeActiveMatch: false });
        }
        return;
      }
    } catch (error) {
      console.warn("Could not refresh job match:", error);
      renderJobMatchProgress(
        "failed_retryable",
        "We couldn’t refresh the status just now. We’ll try again automatically.",
      );
    }

    attempt += 1;
  }

  if (pollToken === activeJobMatchPollToken && activeJobMatchId === matchId) {
    stopJobMatchPolling();
    result.innerHTML = `
      <div class="status-banner status-warning" role="status" aria-live="polite">
        <h3>This job match is taking longer than usual.</h3>
        <p>You may leave this page and check Job Match History later. Use Refresh Matches to check again.</p>
      </div>
    `;
    await loadJobMatches({ resumeActiveMatch: false });
  }
}

async function loadAnalysisDetail(analysisId) {
  result.textContent = "Loading analysis detail...";

  try {
    const response = await fetch(`${API_BASE_URL}/analysis/${analysisId}`, {
      headers: await authHeaders()
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Could not load analysis detail");
    }

    renderAnalysis(data);
    setAccordionOpen("resumeResultCard", true);
  } catch (error) {
    result.textContent = `Error: ${error.message}`;
  }
}

function selectedProvider() {
  return providerSelect ? providerSelect.value : "openai";
}

function showPanel(panelName) {
  if (panelName === "text") {
    textPanel.classList.remove("hidden");
    pdfPanel.classList.add("hidden");

    textTab.classList.add("active");
    pdfTab.classList.remove("active");
  }

  if (panelName === "pdf") {
    pdfPanel.classList.remove("hidden");
    textPanel.classList.add("hidden");

    pdfTab.classList.add("active");
    textTab.classList.remove("active");
  }
}

function jobMatchScoreToneClass(score) {
  return atsScoreToneClass(score);
}

function jobMatchContextMarkup(data, orientation = "vertical") {
  const jobNameValue = data?.jobName || "Untitled Job";
  const resumeNameValue = data?.resumeName || data?.resumeAnalysisName || "Untitled Resume";
  const resumeFileName = data?.resumeFileName || data?.fileName || "";

  return `
    <div class="job-match-context-panels ${escapeHtml(orientation)}">
      <div class="analysis-context-panel">
        <span class="analysis-context-label">Job</span>
        <strong>${escapeHtml(jobNameValue)}</strong>
        ${data?.jobUrl ? `<span class="analysis-context-file">${renderJobUrl(data.jobUrl)}</span>` : ""}
      </div>
      <div class="analysis-context-panel">
        <span class="analysis-context-label">Resume</span>
        <strong>${escapeHtml(resumeNameValue)}</strong>
        ${resumeFileName ? `<span class="analysis-context-file">${escapeHtml(resumeFileName)}</span>` : ""}
      </div>
    </div>
  `;
}

function renderJobMatch(data, tailoring = null, interviewPrep = null) {
  const status = normalizeWorkflowStatus(data.status);

  if (isJobMatchInProgress(status)) {
    renderJobMatchProgress(status);
    return;
  }

  if (isJobMatchFailed(status)) {
    const presentation = jobMatchStatusPresentation(status);
    result.innerHTML = `
      <div class="status-banner status-error" role="alert">
        <h3>${escapeHtml(presentation.label)}</h3>
        <p>${escapeHtml(data.errorMessage || data.message || "Please submit the job match again. If the problem continues, try a shorter job description.")}</p>
      </div>
    `;
    return;
  }

  const matchedKeywords = (data.matchedKeywords || []).map(item => `<li>${escapeHtml(item)}</li>`).join("");
  const missingKeywords = (data.missingKeywords || []).map(item => `<li>${escapeHtml(item)}</li>`).join("");
  const leadershipGaps = (data.leadershipGaps || []).map(item => `<li>${escapeHtml(item)}</li>`).join("");
  const technicalGaps = (data.technicalGaps || []).map(item => `<li>${escapeHtml(item)}</li>`).join("");
  const recommendedChanges = (data.recommendedResumeChanges || []).map(item => `<li>${escapeHtml(item)}</li>`).join("");
  const isCompleted = isJobMatchCompleted(status);
  const resumePreview = data.resumeText ? escapeHtml(data.resumeText.slice(0, 2000)) : "No resume text available.";
  const score = Number(data.matchScore) || 0;

  result.innerHTML = `
    <div class="job-match-result-header-grid">
      <div class="analysis-score-panel job-match-score-panel">
        <span class="analysis-context-label">Match Score</span>
        <div class="score-circle ${escapeHtml(jobMatchScoreToneClass(score))}">${escapeHtml(score)}</div>
      </div>
      <div class="job-match-result-context">
        ${jobMatchContextMarkup(data, "vertical")}
        <div class="metrics job-match-result-metrics">
          <span class="metric status-${escapeHtml(jobMatchStatusPresentation(status).category)}">Status: ${escapeHtml(jobMatchStatusPresentation(status).historyLabel)}</span>
          <span class="metric">Provider: ${escapeHtml(data.provider || "unknown")}</span>
          <span class="metric">Model: ${escapeHtml(data.model || "N/A")}</span>
          <span class="metric">Leadership: ${escapeHtml(data.leadershipMatchScore || 0)}</span>
          <span class="metric">Technical: ${escapeHtml(data.technicalMatchScore || 0)}</span>
          <span class="metric">Architecture: ${escapeHtml(data.architectureMatchScore || 0)}</span>
          <span class="metric">ATS: ${escapeHtml(data.atsKeywordScore || 0)}</span>
          <span class="metric">Duration: ${escapeHtml(data.analysisDurationMs || 0)} ms</span>
        </div>
      </div>
    </div>

    ${isCompleted ? `
      <section class="result-section-panel" aria-labelledby="jobExecutiveSummaryHeading">
        <h3 id="jobExecutiveSummaryHeading">Executive Summary</h3>
        <p>${escapeHtml(data.executiveSummary || "No summary available.")}</p>
        <div class="result-grid">
          <div class="result-box"><h3>Matched Keywords</h3><ul>${matchedKeywords}</ul></div>
          <div class="result-box"><h3>Missing Keywords</h3><ul>${missingKeywords}</ul></div>
          <div class="result-box"><h3>Leadership Gaps</h3><ul>${leadershipGaps}</ul></div>
          <div class="result-box"><h3>Technical Gaps</h3><ul>${technicalGaps}</ul></div>
          <div class="result-box"><h3>Recommended Resume Changes</h3><ul>${recommendedChanges}</ul></div>
        </div>
      </section>
      <section class="result-section-panel result-preview-panel" aria-labelledby="jobResumePreviewHeading">
        <h3 id="jobResumePreviewHeading">Resume Text Preview</h3>
        <div class="resume-preview">${resumePreview}</div>
        ${data.resumeDocumentBucket && data.resumeDocumentKey ? `<div class="resume-download-section"><button class="secondary" onclick="downloadResumeDocument('${escapeHtml(data.resumeAnalysisId)}')">Download Resume PDF</button></div>` : ""}
      </section>
      ${renderTailoringSection(tailoring)}
      ${renderInterviewPrepSection(interviewPrep)}
    ` : `<p><strong>Status:</strong> Job match is still processing. Refresh matches shortly.</p>`}
  `;
}

function jobMatchMissingRequirements() {
  const missing = [];
  if (!jobName?.value.trim()) missing.push("a job name");
  if (!jobUrl?.value.trim()) missing.push("a URL");
  if (!jobDescriptionText?.value.trim()) missing.push("a job description");
  if (!selectedJobResumeAnalysisId) missing.push("a resume");
  return missing;
}

function updateJobMatchAvailability() {
  if (!matchJobButton) return;
  const missing = jobMatchMissingRequirements();
  const ready = missing.length === 0;
  matchJobButton.disabled = !ready;
  if (matchJobButtonTooltip) {
    matchJobButtonTooltip.dataset.tooltip = ready
      ? ""
      : `To enable this button, provide ${missing.join(", ").replace(/, ([^,]*)$/, " and $1")}.`;
  }
}

function completedResumeAnalyses(analyses) {
  return analyses.filter(item =>
    item.status === "completed" &&
    item.analysisId &&
    !item.matchId &&
    item.sourceType
  );
}

function jobResumeCardMarkup(item) {
  const career = analysisTargetCareer(item);
  const roleTitle = career.roleTitle || item.targetRoleTitle || "Target Career unavailable";
  const careerVersion = targetCareerVersionLabel(career);
  const score = Number(item.score) || 0;
  const selected = selectedJobResumeAnalysisId === item.analysisId;

  return `
    <label class="job-resume-option${selected ? " selected" : ""}" data-analysis-id="${escapeHtml(item.analysisId)}">
      <input
        type="radio"
        name="jobResumeAnalysis"
        value="${escapeHtml(item.analysisId)}"
        ${selected ? "checked" : ""}
      />
      <span class="job-resume-copy">
        <span class="job-resume-title-row">
          <strong>${escapeHtml(item.resumeName || "Untitled Resume")}</strong>
          <span class="job-resume-score ${escapeHtml(atsScoreToneClass(score))}">${escapeHtml(score)}</span>
        </span>
        ${item.fileName ? `<span>${escapeHtml(item.fileName)}</span>` : `<span>Text resume</span>`}
        <span>${escapeHtml(roleTitle)} <span class="analysis-context-version">${escapeHtml(careerVersion)}</span></span>
        <span class="job-resume-updated"><em>Analyzed</em> ${escapeHtml(formatEastern(item.createdAt))}</span>
      </span>
    </label>
  `;
}

function selectJobResumeAnalysis(analysisId) {
  selectedJobResumeAnalysisId = analysisId;
  document.querySelectorAll(".job-resume-option").forEach((option) => {
    const selected = option.dataset.analysisId === analysisId;
    option.classList.toggle("selected", selected);
    const input = option.querySelector('input[type="radio"]');
    if (input) input.checked = selected;
  });
  updateJobMatchAvailability();
}

function renderJobResumeCards(analyses) {
  if (!jobResumeList) return;

  const resumes = completedResumeAnalyses(analyses);
  jobResumeLoading?.classList.add("hidden");
  jobResumeError?.classList.add("hidden");

  if (resumes.length === 0) {
    selectedJobResumeAnalysisId = "";
    jobResumeList.innerHTML = "";
    jobResumeEmpty?.classList.remove("hidden");
    updateJobMatchAvailability();
    return;
  }

  jobResumeEmpty?.classList.add("hidden");
  if (!resumes.some(item => item.analysisId === selectedJobResumeAnalysisId)) {
    selectedJobResumeAnalysisId = resumes.length === 1 ? resumes[0].analysisId : "";
  }
  jobResumeList.innerHTML = resumes.map(jobResumeCardMarkup).join("");
  jobResumeList.querySelectorAll(".job-resume-option").forEach((option) => {
    option.addEventListener("click", () => selectJobResumeAnalysis(option.dataset.analysisId));
  });
  if (selectedJobResumeAnalysisId) selectJobResumeAnalysis(selectedJobResumeAnalysisId);
  updateJobMatchAvailability();
}

function populateResumeAnalysisSelect(analyses) {
  if (!resumeAnalysisSelect) return;
  const resumes = completedResumeAnalyses(analyses);
  if (resumes.length === 0) {
    resumeAnalysisSelect.innerHTML = `<option value="">No completed resume analyses available</option>`;
    return;
  }
  resumeAnalysisSelect.innerHTML = resumes.map(item => {
    const label = `${item.resumeName || "Untitled Resume"} | ${formatEastern(item.createdAt)} | ${item.sourceType || "resume"} | score ${item.score || 0} | ${item.fileName || "text resume"}`;
    return `<option value="${escapeHtml(item.analysisId)}">${escapeHtml(label)}</option>`;
  }).join("");
}

async function matchJobDescription() {
  const analysisId = selectedJobResumeAnalysisId || resumeAnalysisSelect?.value || "";
  const jobNameValue = jobName?.value.trim() || "";
  const jobUrlValue = jobUrl?.value.trim() || "";
  const jdText = jobDescriptionText?.value.trim() || "";

  if (!analysisId) {
    result.textContent = "Select a resume analysis first.";
    focusAccordionCard("jobResultCard");
    return;
  }

  if (!jobNameValue || !jobUrlValue || !jdText) {
    result.textContent = "Provide a job name, URL, and job description first.";
    focusAccordionCard("jobResultCard");
    return;
  }

  const idempotencyKey = crypto.randomUUID();

  stopJobMatchPolling();
  setButtonLoading(matchJobButton, "Submitting...");
  renderJobMatchProgress("queued_pending_dispatch", "We’re submitting the job description and preparing your match.");
  transitionToJobMatchResult();

  try {
    const headers = await jsonHeaders();
    headers["Idempotency-Key"] = idempotencyKey;

    const response = await fetch(
      `${API_BASE_URL}/match-job-description`,
      {
        method: "POST",
        headers,
        body: JSON.stringify({
          analysisId,
          jobName: jobNameValue,
          jobUrl: jobUrlValue,
          jobDescriptionText: jdText,
          analysisProvider: selectedProvider(),
        }),
      },
    );

    const data = await response.json();

    if (!response.ok) {
      const message = data?.error?.message || data?.error || "Job match failed";
      throw new Error(message);
    }

    renderJobMatch(data);
    setAccordionOpen("jobResultCard", true);
    await loadJobMatches({ resumeActiveMatch: false });

    const matchId = data.matchId;
    if (matchId && isJobMatchInProgress(data.status)) {
      void pollJobMatchUntilComplete(matchId);
    }

    setButtonSaved(matchJobButton, "Submitted ✓");
  } catch (error) {
    stopJobMatchPolling();
    result.innerHTML = `
      <div class="status-banner status-error" role="alert">
        <h3>We couldn’t submit this job match.</h3>
        <p>${escapeHtml(error.message)}</p>
      </div>
    `;
    resetButton(matchJobButton);
  }
}

async function loadJobMatches({ resumeActiveMatch = true } = {}) {
  if (!jobMatches) {
    return;
  }

  if (resumeActiveMatch || cachedJobMatches.length === 0) {
    jobMatches.textContent = "Loading job matches...";
  }

  try {
    const response = await fetch(`${API_BASE_URL}/job-matches`, {
      headers: await authHeaders()
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Could not load job matches");
    }

    cachedJobMatches = data.jobMatches || [];
    renderJobMatchHistory();

    applyDefaultJobAccordionState();

    if (resumeActiveMatch && !deepLinkMatchId) {
      const activeMatch = [...cachedJobMatches]
        .filter(item => item.matchId && isJobMatchInProgress(item.status))
        .sort((a, b) => new Date(b.createdAt || 0) - new Date(a.createdAt || 0))[0];

      if (activeMatch) {
        setAccordionOpen("matchJobCard", false);
        setAccordionOpen("jobResultCard", true);
        renderJobMatch(activeMatch);
        void pollJobMatchUntilComplete(activeMatch.matchId);
      }
    }

    if (deepLinkMatchId) {
      openJobDetailView();
      await loadJobMatchDetail(deepLinkMatchId);
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  } catch (error) {
    jobMatches.textContent = `Error: ${error.message}`;
  }
}

async function loadJobMatchDetail(matchId) {
  result.textContent = "Loading job match detail...";

  try {
    const response = await fetch(`${API_BASE_URL}/job-match/${matchId}`, {
      headers: await authHeaders()
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Could not load job match detail");
    }

    const tailoring = await fetchTailoringForMatch(matchId);
    const interviewPrep = await fetchInterviewPrepForMatch(matchId);

    renderJobMatch(data, tailoring, interviewPrep);
    setAccordionOpen("jobResultCard", true);

    if (isJobMatchInProgress(data.status)) {
      void pollJobMatchUntilComplete(matchId);
    }
  } catch (error) {
    result.textContent = `Error: ${error.message}`;
  }
}

async function deleteAnalysis(
  analysisId,
  version = 0,
) {
  const confirmed = confirm(
    "Delete this resume analysis? This cannot be undone.",
  );

  if (!confirmed) {
    return;
  }

  const expectedVersion = Number(version ?? 0);

  try {
    const response = await fetch(
      `${API_BASE_URL}/analysis/${encodeURIComponent(
        analysisId,
      )}?version=${encodeURIComponent(
        expectedVersion,
      )}`,
      {
        method: "DELETE",
        headers: await authHeaders(),
      },
    );

    const data = await response.json();

    if (response.status === 409) {
      throw new Error(
        data?.error?.message
        || (
          "This resume analysis changed before it "
          + "could be deleted. Refresh the list and "
          + "try again."
        ),
      );
    }

    if (!response.ok) {
      throw new Error(
        data?.error?.message
        || data?.error
        || "Delete failed",
      );
    }

    result.textContent =
      "Resume analysis deleted.";

    await loadHistory();
  } catch (error) {
    result.textContent =
      `Error: ${error.message}`;
  }
}

async function deleteAllAnalyses() {
  const confirmed = confirm(
    "Delete all resume analyses? This cannot be undone.",
  );

  if (!confirmed) {
    return;
  }

  try {
    const response = await fetch(
      `${API_BASE_URL}/analyses`,
      {
        method: "DELETE",
        headers: await authHeaders(),
      },
    );

    const data = await response.json();

    if (!response.ok) {
      throw new Error(
        data?.error?.message
        || data?.error
        || "Delete all failed",
      );
    }

    result.textContent =
      `Resume analyses: ${Number(data.deleted ?? 0)} deleted, `
      + `${Number(data.conflicted ?? 0)} conflicted, `
      + `${Number(data.failed ?? 0)} failed.`;

    await loadHistory();
  } catch (error) {
    result.textContent =
      `Error: ${error.message}`;
  }
}

async function deleteJobMatch(
  matchId,
  version = 0,
) {
  const confirmed = confirm(
    "Delete this job match? This cannot be undone.",
  );

  if (!confirmed) {
    return;
  }

  const expectedVersion = Number(version ?? 0);

  try {
    const response = await fetch(
      `${API_BASE_URL}/job-match/${encodeURIComponent(
        matchId,
      )}?version=${encodeURIComponent(
        expectedVersion,
      )}`,
      {
        method: "DELETE",
        headers: await authHeaders(),
      },
    );

    const data = await response.json();

    if (response.status === 409) {
      throw new Error(
        data?.error?.message
        || (
          "This job match changed before it could "
          + "be deleted. Refresh the list and try "
          + "again."
        ),
      );
    }

    if (!response.ok) {
      throw new Error(
        data?.error?.message
        || data?.error
        || "Delete failed",
      );
    }

    result.textContent = "Job match deleted.";

    await loadJobMatches();
  } catch (error) {
    result.textContent =
      `Error: ${error.message}`;
  }
}

async function deleteAllJobMatches() {
  const confirmed = confirm(
    "Delete all job matches? This cannot be undone.",
  );

  if (!confirmed) {
    return;
  }

  try {
    const response = await fetch(
      `${API_BASE_URL}/job-matches`,
      {
        method: "DELETE",
        headers: await authHeaders(),
      },
    );

    const data = await response.json();

    if (!response.ok) {
      throw new Error(
        data?.error?.message
        || data?.error
        || "Delete all failed",
      );
    }

    result.textContent =
      `Job matches: ${Number(data.deleted ?? 0)} deleted, `
      + `${Number(data.conflicted ?? 0)} conflicted, `
      + `${Number(data.failed ?? 0)} failed.`;

    await loadJobMatches();
  } catch (error) {
    result.textContent =
      `Error: ${error.message}`;
  }
}

async function downloadResumeDocument(analysisId) {
  try {
    const response = await fetch(`${API_BASE_URL}/analysis/${analysisId}/download-url`, {
      headers: await authHeaders()
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Could not create download URL");
    }

    window.open(data.downloadUrl, "_blank");
  } catch (error) {
    result.textContent = `Error: ${error.message}`;
  }
}

function formatEastern(value) {
  if (!value) {
    return "unknown date";
  }

  return new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short"
  }).format(new Date(value));
}

function renderResumeLabelFromJobMatch(data) {
  return (
    `${data.resumeName || "Untitled Resume"} | ` +
    `${formatEastern(data.resumeCreatedAt)} | ` +
    `${data.resumeSourceType || "resume"} | ` +
    `score ${data.resumeScore || 0} | ` +
    `${data.resumeFileName || "text resume"}`
  );
}

function renderJobUrl(url) {
  if (!url) {
    return "N/A";
  }

  const safeUrl = escapeHtml(url);

  return `<a href="${safeUrl}" target="_blank" rel="noopener noreferrer">${safeUrl}</a>`;
}

function countByStatus(items) {
  return items.reduce(
    (counts, item) => {
      const status = item.status || "unknown";
      counts.total += 1;
      counts[status] = (counts[status] || 0) + 1;
      return counts;
    },
    { total: 0 }
  );
}

function renderStatusSummary(container, label, items, presentationForStatus = analysisStatusPresentation) {
  if (!container) {
    return;
  }

  const counts = items.reduce(
    (summary, item) => {
      const category = presentationForStatus(item.status).category;
      summary.total += 1;
      summary[category] += 1;
      return summary;
    },
    { total: 0, completed: 0, processing: 0, failed: 0 },
  );

  container.innerHTML = `
    <span><strong>${escapeHtml(label)}:</strong> ${escapeHtml(String(counts.total))}</span>
    <span>Complete: ${escapeHtml(String(counts.completed))}</span>
    <span>In progress: ${escapeHtml(String(counts.processing))}</span>
    <span>Needs attention: ${escapeHtml(String(counts.failed))}</span>
  `;
}

function sortItems(items, sortValue, scoreField) {
  const sorted = [...items];

  if (sortValue === "oldest") {
    sorted.sort((a, b) => new Date(a.createdAt || 0) - new Date(b.createdAt || 0));
  } else if (sortValue === "highestScore") {
    sorted.sort((a, b) => Number(b[scoreField] || 0) - Number(a[scoreField] || 0));
  } else if (sortValue === "lowestScore") {
    sorted.sort((a, b) => Number(a[scoreField] || 0) - Number(b[scoreField] || 0));
  } else if (sortValue === "processingFirst") {
    sorted.sort((a, b) => {
      const aProcessing = isAnalysisInProgress(a.status) ? 0 : 1;
      const bProcessing = isAnalysisInProgress(b.status) ? 0 : 1;

      if (aProcessing !== bProcessing) {
        return aProcessing - bProcessing;
      }

      return new Date(b.createdAt || 0) - new Date(a.createdAt || 0);
    });
  } else {
    sorted.sort((a, b) => new Date(b.createdAt || 0) - new Date(a.createdAt || 0));
  }

  return sorted;
}

function toggleCardDetails(id) {
  const element = document.getElementById(id);

  if (!element) {
    return;
  }

  element.classList.toggle("hidden");
}

async function hydrateResumePdfPreviews() {
  const previewElements = document.querySelectorAll("[data-pdf-analysis-id]");

  await Promise.all(Array.from(previewElements).map(async (element) => {
    const analysisId = element.dataset.pdfAnalysisId;
    if (!analysisId || element.dataset.loaded === "true") return;

    element.dataset.loaded = "true";

    try {
      const response = await fetch(`${API_BASE_URL}/analysis/${encodeURIComponent(analysisId)}/download-url`, {
        headers: await authHeaders(),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data?.error?.message || data?.error || "Could not load PDF preview");
      }

      const previewUrl = `${data.downloadUrl}#page=1&view=FitH&toolbar=0&navpanes=0&scrollbar=0`;
      element.innerHTML = `
        <iframe
          class="pdf-thumbnail-frame"
          src="${escapeHtml(previewUrl)}"
          title="First-page preview of ${escapeHtml(data.resumeName || data.fileName || "uploaded resume")}">
        </iframe>
      `;
    } catch (error) {
      element.innerHTML = `<div class="pdf-thumbnail-fallback">PDF preview unavailable. Use Download PDF to open the file.</div>`;
    }
  }));
}

function renderResumeHistory() {
  if (!history) {
    return;
  }

  const searchValue = resumeSearchInput?.value.trim().toLowerCase() || "";
  const sortValue = resumeSortSelect?.value || "newest";

  let filtered = cachedResumeAnalyses.filter(item => {
    const name = (item.resumeName || "Untitled Resume").toLowerCase();
    const text = (item.resumeText || "").toLowerCase();
    return name.includes(searchValue) || text.includes(searchValue);
  });

  filtered = sortItems(filtered, sortValue, "score");

  renderStatusSummary(resumeSummary, "Total Resumes", cachedResumeAnalyses);
  populateResumeAnalysisSelect(cachedResumeAnalyses);

  if (filtered.length === 0) {
    history.textContent = "No resume analyses found.";
    return;
  }

  history.innerHTML = filtered.map(item => {
    const score = item.score || item.overallScore || 0;
    const career = analysisTargetCareer(item);
    const roleTitle = career.roleTitle || item.targetRoleTitle || "Target Career unavailable";
    const careerVersion = targetCareerVersionLabel(career);
    const resumeName = item.resumeName || "Untitled Resume";
    const fileName = item.fileName || "";

    return `
      <div class="history-item resume-history-card">
        <div class="resume-history-main-grid">
          <div class="history-score-cell">
            <div class="score-circle ${atsScoreToneClass(score)}" aria-label="ATS score ${escapeHtml(score)}">${escapeHtml(score)}</div>
          </div>

          <div class="resume-history-left-stack">
            <div class="analysis-context-panel">
              <span class="analysis-context-label">Target Career</span>
              <strong>${escapeHtml(roleTitle)} <span class="analysis-context-version">${escapeHtml(careerVersion)}</span></strong>
            </div>

            <div class="analysis-context-panel">
              <span class="analysis-context-label">Resume</span>
              <strong>${escapeHtml(resumeName)}</strong>
              ${fileName ? `<span class="analysis-context-file">${escapeHtml(fileName)}</span>` : ""}
            </div>

            <div class="resume-history-controls-panel">
              <div class="history-metrics">
                <span class="badge status-${escapeHtml(analysisStatusPresentation(item.status).category)}">${escapeHtml(analysisStatusPresentation(item.status).historyLabel)}</span>
                <span class="badge">Created: ${escapeHtml(formatEastern(item.createdAt))}</span>
                <span class="badge">${escapeHtml(item.provider || "unknown")}</span>
                <span class="badge">Words: ${escapeHtml(item.wordCount || 0)}</span>
                <span class="badge">Duration: ${escapeHtml(item.analysisDurationMs || 0)} ms</span>
                <span class="badge">Model: ${escapeHtml(item.model || "N/A")}</span>
                <span class="badge">Version: ${escapeHtml(item.analysisVersion || "N/A")}</span>
              </div>

              <div class="button-row">
                <button class="secondary" onclick="loadAnalysisDetail('${escapeHtml(item.analysisId)}')">View Details</button>
                ${
                  item.documentBucket && item.documentKey
                    ? `<button class="secondary" onclick="downloadResumeDocument('${escapeHtml(item.analysisId)}')">Download PDF</button>`
                    : ""
                }
                <button class="danger" onclick="deleteAnalysis('${escapeHtml(item.analysisId)}', ${Number(item.version ?? 0)})">Delete</button>
              </div>
            </div>
          </div>

          <div class="resume-history-right">
            ${analysisPreviewMarkup(item, true)}
          </div>
        </div>
      </div>
    `;
  }).join("");
  hydrateResumePdfPreviews();
}

function renderJobMatchHistory() {
  if (!jobMatches) return;

  const searchValue = jobSearchInput?.value.trim().toLowerCase() || "";
  const sortValue = jobSortSelect?.value || "newest";
  let filtered = cachedJobMatches.filter(item => {
    const name = (item.jobName || "Untitled Job").toLowerCase();
    const description = (item.jobDescriptionText || "").toLowerCase();
    return name.includes(searchValue) || description.includes(searchValue);
  });
  filtered = sortItems(filtered, sortValue, "matchScore");
  renderStatusSummary(jobMatchSummary, "Total Matches", cachedJobMatches, jobMatchStatusPresentation);

  if (filtered.length === 0) {
    jobMatches.textContent = "No job matches found.";
    return;
  }

  jobMatches.innerHTML = filtered.map(item => {
    const score = Number(item.matchScore) || 0;
    const resumeNameValue = item.resumeName || item.resumeAnalysisName || "Untitled Resume";
    const resumeFileName = item.resumeFileName || item.fileName || "";
    const jobPreview = item.jobDescriptionText
      ? escapeHtml(item.jobDescriptionText.slice(0, 1200))
      : "No job description stored.";
    const presentation = jobMatchStatusPresentation(item.status);

    return `
      <div class="history-item job-match-history-card">
        <div class="job-match-history-grid">
          <div class="history-score-cell job-match-history-score">
            <div class="score-circle ${escapeHtml(jobMatchScoreToneClass(score))}">${escapeHtml(score)}</div>
          </div>

          <div class="job-match-history-left">
            <div class="analysis-context-panel">
              <span class="analysis-context-label">Job</span>
              <strong>${escapeHtml(item.jobName || "Untitled Job")}</strong>
              ${item.jobUrl ? `<span class="analysis-context-file">${renderJobUrl(item.jobUrl)}</span>` : ""}
            </div>
            <div class="analysis-context-panel">
              <span class="analysis-context-label">Resume</span>
              <strong>${escapeHtml(resumeNameValue)}</strong>
              ${resumeFileName ? `<span class="analysis-context-file">${escapeHtml(resumeFileName)}</span>` : ""}
            </div>
            <div class="job-match-history-controls">
              <div class="history-metrics">
                <span class="badge status-${escapeHtml(presentation.category)}">${escapeHtml(presentation.historyLabel)}</span>
                <span class="badge">Provider: ${escapeHtml(item.provider || "unknown")}</span>
                <span class="badge">Leadership: ${escapeHtml(item.leadershipMatchScore || 0)}</span>
                <span class="badge">Technical: ${escapeHtml(item.technicalMatchScore || 0)}</span>
                <span class="badge">Architecture: ${escapeHtml(item.architectureMatchScore || 0)}</span>
                <span class="badge">ATS: ${escapeHtml(item.atsKeywordScore || 0)}</span>
                <span class="badge">Duration: ${escapeHtml(item.analysisDurationMs || 0)} ms</span>
                <span class="badge">Model: ${escapeHtml(item.model || "N/A")}</span>
              </div>
              <div class="button-row">
                <button class="secondary" onclick="loadJobMatchDetail('${escapeHtml(item.matchId)}')">View Details</button>
                <button class="danger" onclick="deleteJobMatch('${escapeHtml(item.matchId)}', ${Number(item.version ?? 0)})">Delete</button>
              </div>
            </div>
          </div>

          <div class="job-match-history-preview">
            <div class="resume-preview small-preview">${jobPreview}</div>
          </div>
        </div>
      </div>
    `;
  }).join("");
}

function renderResumeTailoring(data) {
  const isCompleted = data.status === "completed";
  const statusClass = isCompleted ? "" : "status-pending";

  result.innerHTML = `
    <div class="score-card">
      <div class="score-circle">T</div>
      <div>
        <h3>Resume Tailoring</h3>
        <p><strong>Tailoring ID:</strong> ${escapeHtml(data.tailoringId || data.analysisId || "")}</p>
        <p><strong>Job:</strong> ${escapeHtml(data.jobName || "Untitled Job")}</p>
        <p><strong>Resume:</strong> ${escapeHtml(data.resumeName || "Untitled Resume")}</p>
        <p><strong>Created:</strong> ${escapeHtml(formatEastern(data.createdAt))}</p>
      </div>
    </div>

    <div class="metrics">
      <span class="metric ${statusClass}">Status: ${escapeHtml(data.status || "unknown")}</span>
      <span class="metric">Provider: ${escapeHtml(data.provider || "unknown")}</span>
      <span class="metric">Model: ${escapeHtml(data.model || "N/A")}</span>
      <span class="metric">Duration: ${escapeHtml(data.analysisDurationMs || 0)} ms</span>
    </div>

    ${isCompleted ? `
      <h3>Tailored Executive Summary</h3>
      <p>${escapeHtml(data.tailoredExecutiveSummary || "No tailored summary available.")}</p>

      <div class="result-box">
        <h3>Tailored Resume Bullets</h3>
        <ul>${listToHtml(data.tailoredResumeBullets)}</ul>
      </div>

      <div class="result-grid">
        <div class="result-box">
          <h3>Keywords to Add</h3>
          <ul>${listToHtml(data.keywordsToAdd)}</ul>
        </div>

        <div class="result-box">
          <h3>Role Positioning Advice</h3>
          <ul>${listToHtml(data.rolePositioningAdvice)}</ul>
        </div>
      </div>

      <div class="result-grid">
        <div class="result-box">
          <h3>ATS Optimization Advice</h3>
          <ul>${listToHtml(data.atsOptimizationAdvice)}</ul>
        </div>

        <div class="result-box">
          <h3>Rewrite Warnings</h3>
          <ul>${listToHtml(data.rewriteWarnings)}</ul>
        </div>
      </div>
    ` : `
      <p><strong>Status:</strong> Resume tailoring is still processing. Refresh tailorings shortly.</p>
    `}
  `;
}

async function fetchTailoringForMatch(matchId) {
  try {
    const response = await fetch(`${API_BASE_URL}/job-match/${matchId}/tailoring`, {
      headers: await authHeaders()
    });
    const data = await response.json();

    if (!response.ok) {
      return null;
    }

    return data;
  } catch {
    return null;
  }
}

function renderTailoringSection(tailoring) {
  if (!tailoring) {
    return `
      <section class="result-box">
        <h3>Resume Tailoring</h3>
        <p>No tailoring result found yet. Refresh this job match shortly.</p>
      </section>
    `;
  }

  const isCompleted = tailoring.status === "completed";
  const statusClass = isCompleted ? "" : "status-pending";

  return `
    <section class="result-box">
      <h3>Resume Tailoring</h3>

      <div class="metrics">
        <span class="metric ${statusClass}">Status: ${escapeHtml(tailoring.status || "unknown")}</span>
        <span class="metric">Provider: ${escapeHtml(tailoring.provider || "unknown")}</span>
        <span class="metric">Model: ${escapeHtml(tailoring.model || "N/A")}</span>
        <span class="metric">Duration: ${escapeHtml(tailoring.analysisDurationMs || 0)} ms</span>
      </div>

      ${isCompleted ? `
        <h4>Tailored Executive Summary</h4>
        <p>${escapeHtml(tailoring.tailoredExecutiveSummary || "No tailored summary available.")}</p>

        <h4>Tailored Resume Bullets</h4>
        <ul>${listToHtml(tailoring.tailoredResumeBullets)}</ul>

        <div class="result-grid">
          <div class="result-box">
            <h4>Keywords to Add</h4>
            <ul>${listToHtml(tailoring.keywordsToAdd)}</ul>
          </div>

          <div class="result-box">
            <h4>Role Positioning Advice</h4>
            <ul>${listToHtml(tailoring.rolePositioningAdvice)}</ul>
          </div>
        </div>

        <div class="result-grid">
          <div class="result-box">
            <h4>ATS Optimization Advice</h4>
            <ul>${listToHtml(tailoring.atsOptimizationAdvice)}</ul>
          </div>

          <div class="result-box">
            <h4>Rewrite Warnings</h4>
            <ul>${listToHtml(tailoring.rewriteWarnings)}</ul>
          </div>
        </div>
      ` : `
        <p><strong>Status:</strong> Resume tailoring is still processing. Refresh this job match shortly.</p>
      `}
    </section>
  `;
}

async function fetchInterviewPrepForMatch(matchId) {
  try {
    const response = await fetch(`${API_BASE_URL}/job-match/${matchId}/interview-prep`, {
      headers: await authHeaders()
    });

    const data = await response.json();

    if (!response.ok) {
      return null;
    }

    return data;
  } catch {
    return null;
  }
}

function renderQuestionItems(items) {
  if (!items || items.length === 0) {
    return "<p>No questions available yet.</p>";
  }

  return items.map((item, index) => `
    <div class="question-card">
      <p><strong>${index + 1}. ${escapeHtml(item.question || "")}</strong></p>

      <p><strong>Answer Framework</strong></p>
      <ul>${listToHtml(item.answerFramework || [])}</ul>

      <p><strong>Follow-up Questions</strong></p>
      <ul>${listToHtml(item.followUpQuestions || [])}</ul>
    </div>
  `).join("");
}

function renderInterviewQuestionSection(title, questions) {
  return `
    <details class="interview-section">
      <summary>${escapeHtml(title)}</summary>
      ${renderQuestionItems(questions)}
    </details>
  `;
}

function renderInterviewPrepSection(interviewPrep) {
  if (!interviewPrep) {
    return `
      <section class="result-box">
        <h3>Interview Preparation</h3>
        <p>No interview preparation result found yet. Refresh this job match shortly.</p>
      </section>
    `;
  }

  const isCompleted = interviewPrep.status === "completed";
  const statusClass = isCompleted ? "" : "status-pending";

  return `
    <section class="result-box">
      <h3>Interview Preparation</h3>

      <div class="metrics">
        <span class="metric ${statusClass}">Status: ${escapeHtml(interviewPrep.status || "unknown")}</span>
        <span class="metric">Provider: ${escapeHtml(interviewPrep.provider || "unknown")}</span>
        <span class="metric">Model: ${escapeHtml(interviewPrep.model || "N/A")}</span>
        <span class="metric">Duration: ${escapeHtml(interviewPrep.analysisDurationMs || 0)} ms</span>
      </div>

      ${isCompleted ? `
        <h4>Interview Readiness Summary</h4>
        <p>${escapeHtml(interviewPrep.interviewReadinessSummary || "No summary available.")}</p>

        ${renderInterviewQuestionSection("Behavioral Questions", interviewPrep.behavioralQuestions)}
        ${renderInterviewQuestionSection("Leadership Questions", interviewPrep.leadershipQuestions)}
        ${renderInterviewQuestionSection("System Design Questions", interviewPrep.systemDesignQuestions)}
        ${renderInterviewQuestionSection("Cloud Architecture Questions", interviewPrep.cloudArchitectureQuestions)}
        ${renderInterviewQuestionSection("Security Questions", interviewPrep.securityQuestions)}
        ${renderInterviewQuestionSection("Resume-Specific Questions", interviewPrep.resumeSpecificQuestions)}
        ${renderInterviewQuestionSection("Job-Specific Questions", interviewPrep.jobSpecificQuestions)}
      ` : `
        <p><strong>Status:</strong> Interview preparation is still processing. Refresh this job match shortly.</p>
      `}
    </section>
  `;
}

async function applyPreferredProviderFromProfile() {
  if (!providerSelect) {
    return;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/profile`, {
      headers: await authHeaders()
    });

    const profile = await response.json();

    if (!response.ok) {
      return;
    }

    if (profile.preferredProvider) {
      providerSelect.value = profile.preferredProvider;
    }
  } catch (error) {
    console.warn("Could not load preferred provider:", error);
  }
}

window.refreshAnalysisHistory = async function (event) {
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }

  setAccordionOpen("analysisHistoryCard", true);

  if (history) {
    history.textContent = "Refreshing history...";
  }

  await loadHistory();
};

window.refreshJobMatchHistory = async function (event) {
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }

  setAccordionOpen("jobHistoryCard", true);

  if (jobMatches) {
    jobMatches.textContent = "Refreshing job matches...";
  }

  await loadJobMatches();
};

window.deleteAllJobMatches = deleteAllJobMatches;

function listToHtml(items) {
  return (items || [])
    .map(item => `<li>${escapeHtml(item)}</li>`)
    .join("");
}

function focusAccordionCard(cardId, moveFocus = false) {
  setAccordionOpen(cardId, true);

  const card = document.getElementById(cardId);

  if (card) {
    card.scrollIntoView({
      behavior: "smooth",
      block: "start"
    });

    if (moveFocus) {
      const summary = card.querySelector("summary");
      if (summary) {
        summary.focus({ preventScroll: true });
      }
    }
  }
}

function renderDynamicScores(dynamicScores) {
  if (!dynamicScores || dynamicScores.length === 0) {
    return "<p>No role-specific scores available.</p>";
  }

  return `
    <div class="result-grid">
      ${dynamicScores.map(score => `
        <div class="result-box">
          <h3>${escapeHtml(score.label || score.key || "Score")}</h3>
          <div class="score">${escapeHtml(score.score ?? 0)}</div>
          <p>${escapeHtml(score.explanation || "")}</p>
        </div>
      `).join("")}
    </div>
  `;
}

function setButtonLoading(button, label) {
  if (!button) return;

  button.disabled = true;
  button.dataset.originalText = button.dataset.originalText || button.textContent;
  button.textContent = label;
}

function setButtonSaved(button, label = "Queued ✓", resetDelayMs = 2000) {
  if (!button) return;

  button.disabled = true;
  button.textContent = label;

  setTimeout(() => {
    resetButton(button);
  }, resetDelayMs);
}

function resetButton(button) {
  if (!button) return;

  button.disabled = false;
  button.textContent = button.dataset.originalText || button.textContent;
}

window.addEventListener("pagehide", () => {
  stopAnalysisPolling();
  stopJobMatchPolling();
  if (analysisTransitionTimer) {
    clearTimeout(analysisTransitionTimer);
  }
  if (jobMatchTransitionTimer) {
    clearTimeout(jobMatchTransitionTimer);
  }
});

setupAccordionPersistence();

if (analyzeButton) {
  analyzeButton.addEventListener("click", analyzeTextResume);
}

if (uploadButton) {
  uploadButton.addEventListener("click", uploadPdfResume);
}

[resumeName, textarea, fileInput].forEach((input) => {
  input?.addEventListener("input", updateResumeAnalysisAvailability);
  input?.addEventListener("change", updateResumeAnalysisAvailability);
});

if (refreshHistoryButton) {
  refreshHistoryButton.addEventListener("click", async (event) => {
    event.preventDefault();
    event.stopPropagation();

    setAccordionOpen("analysisHistoryCard", true);

    if (history) {
      history.textContent = "Refreshing history...";
    }

    await loadHistory();
  });
}

if (deleteAllAnalysesButton) {
  deleteAllAnalysesButton.addEventListener("click", deleteAllAnalyses);
}

[jobName, jobUrl, jobDescriptionText].forEach((input) => {
  input?.addEventListener("input", updateJobMatchAvailability);
  input?.addEventListener("change", updateJobMatchAvailability);
});

if (matchJobButton) {
  matchJobButton.addEventListener("click", matchJobDescription);
  updateJobMatchAvailability();
}

if (refreshJobMatchesButton) {
  refreshJobMatchesButton.addEventListener("click", async (event) => {
    event.preventDefault();
    event.stopPropagation();

    setAccordionOpen("jobHistoryCard", true);

    if (jobMatches) {
      jobMatches.textContent = "Refreshing job matches...";
    }

    await loadJobMatches();
  });
}

if (deleteAllJobMatchesButton) {
  deleteAllJobMatchesButton.addEventListener("click", deleteAllJobMatches);
}

if (resumeSearchInput) {
  resumeSearchInput.addEventListener("input", renderResumeHistory);
}

if (resumeSortSelect) {
  resumeSortSelect.addEventListener("change", renderResumeHistory);
}

if (jobSearchInput) {
  jobSearchInput.addEventListener("input", renderJobMatchHistory);
}

if (jobSortSelect) {
  jobSortSelect.addEventListener("change", renderJobMatchHistory);
}

if (textTab) {
  textTab.addEventListener("click", () => showPanel("text"));
}

if (pdfTab) {
  pdfTab.addEventListener("click", () => showPanel("pdf"));
}

if (page === "resume-analysis") {
  Promise.all([
    applyPreferredProviderFromProfile(),
    loadResumeTargetCareers(),
  ]).then(loadHistory);
}

if (page === "job-matching") {
  applyPreferredProviderFromProfile().then(() => {
    loadHistory();
    loadJobMatches();
  });
}
