const API_BASE_URL = window.APP_CONFIG?.apiEndpoint;

if (!API_BASE_URL) {
  throw new Error("Missing API endpoint configuration");
}

const page = document.body.dataset.page;

const analyzeButton = document.getElementById("analyzeButton");
const uploadButton = document.getElementById("uploadButton");
const refreshHistoryButton = document.getElementById("refreshHistoryButton");
const deleteAllAnalysesButton = document.getElementById("deleteAllAnalysesButton");

const matchJobButton = document.getElementById("matchJobButton");
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
const jobName = document.getElementById("jobName");
const jobUrl = document.getElementById("jobUrl");
const jobDescriptionText = document.getElementById("jobDescriptionText");
const jobMatches = document.getElementById("jobMatches");

const resumeName = document.getElementById("resumeName");

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

function renderAnalysis(data) {
  const strengths = (data.strengths || [])
    .map(item => `<li>${escapeHtml(item)}</li>`)
    .join("");

  const recommendations = (data.recommendations || [])
    .map(item => `<li>${escapeHtml(item)}</li>`)
    .join("");

  const score = data.score || data.overallScore || 0;
  const resumePreview = data.resumeText
    ? escapeHtml(data.resumeText.slice(0, 2000))
    : "No resume text stored.";

  const leadershipGaps = (data.leadershipGaps || [])
    .map(item => `<li>${escapeHtml(item)}</li>`)
    .join("");

  const technicalGaps = (data.technicalGaps || [])
    .map(item => `<li>${escapeHtml(item)}</li>`)
    .join("");

  const isCompleted = data.status === "completed";
  const statusClass = isCompleted ? "" : "status-pending";

  result.innerHTML = `
    <div class="score-card">
      <div class="score-circle">${score}</div>
      <div>
        <h3>Resume Analysis Complete</h3>
        <!-- <p><strong>Analysis ID:</strong> ${escapeHtml(data.analysisId)}</p> -->
        <p><strong>Created:</strong> ${escapeHtml(formatEastern(data.createdAt))}</p>
        <p><strong>File:</strong> ${escapeHtml(data.fileName || "N/A")}</p>
      </div>
    </div>

    <div class="metrics">
      <span class="metric">Model: ${escapeHtml(data.model || "N/A")}</span>
      <span class="metric">Source: ${escapeHtml(data.sourceType || "text")}</span>
      <span class="metric ${statusClass}">Status: ${escapeHtml(data.status || "unknown")}</span>
      <span class="metric">Provider: ${escapeHtml(data.provider || "rule-based")}</span>
      <span class="metric">Version: ${escapeHtml(data.analysisVersion || "unknown")}</span>
      <span class="metric">Words: ${escapeHtml(data.wordCount || 0)}</span>
      <span class="metric">Duration: ${escapeHtml(data.analysisDurationMs || 0)} ms</span>
    </div>

    <h3>Target Career</h3>
    <p><strong>Role:</strong> ${escapeHtml(data.targetRoleTitle || "Not specified")}</p>
    <p><strong>Industry:</strong> ${escapeHtml(data.targetIndustry || "Not specified")}</p>

    <h3>Role-Specific Scores</h3>
    ${renderDynamicScores(data.dynamicScores)}

    <h3>Role Fit Summary</h3>
    <p>${escapeHtml(data.roleFitSummary || "")}</p>

    <h3>Role-Specific Gaps</h3>
    <ul>${listToHtml(data.roleSpecificGaps || [])}</ul>

    ${isCompleted ? `
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
 
      <h3>Resume Text Preview</h3>
      <div class="resume-preview">${resumePreview}</div>
  ` : `
    <p><strong>Status:</strong> Resume analysis is still processing. Refresh history shortly.</p>
  `}
  `;
}

async function analyzeTextResume() {
  const resumeTextValue = textarea.value.trim();

  if (!resumeTextValue) {
    result.textContent = "Please enter resume text.";
    return;
  }

  setButtonLoading(analyzeTextButton, "Analyzing...");
  result.textContent = "Analyzing resume text...";
  focusAccordionCard("resumeResultCard");

  try {
    const response = await fetch(`${API_BASE_URL}/analyze-resume`, {
      method: "POST",
      headers: await jsonHeaders(),
      body: JSON.stringify({
        resumeName: resumeName?.value.trim() || "Untitled Resume",
        resumeText: resumeTextValue,
        analysisProvider: selectedProvider()
      })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Text analysis failed");
    }

    renderAnalysis(data);
    setAccordionOpen("resumeResultCard", true);
    await loadHistory();

    setButtonSaved(analyzeTextButton, "Complete ✓");
  } catch (error) {
    result.textContent = `Error: ${error.message}`;
    resetButton(analyzeTextButton);
  }
}

async function uploadPdfResume() {
  const file = fileInput.files[0];

  if (!file) {
    result.textContent = "Choose a PDF file first.";
    return;
  }

  if (file.type !== "application/pdf") {
    result.textContent = "Only PDF files are supported.";
    return;
  }

  setButtonLoading(uploadButton, "Uploading...");
  focusAccordionCard("resumeResultCard");
  result.textContent = "Uploading and analyzing PDF...";

  try {
    const uploadUrlResponse = await fetch(`${API_BASE_URL}/resume-upload-url`, {
      method: "POST",
      headers: await jsonHeaders(),
      body: JSON.stringify({
        fileName: file.name,
        contentType: file.type
      })
    });

    const uploadData = await uploadUrlResponse.json();

    if (!uploadUrlResponse.ok) {
      throw new Error(uploadData.error || "Could not create upload URL");
    }

    result.textContent = "Uploading PDF...";

    const uploadResponse = await fetch(uploadData.uploadUrl, {
      method: "PUT",
      headers: {
        "Content-Type": file.type
      },
      body: file
    });

    if (!uploadResponse.ok) {
      throw new Error("PDF upload failed");
    }

    result.textContent = "Saving PDF analysis metadata...";

    const analysisResponse = await fetch(`${API_BASE_URL}/analyze-uploaded-resume`, {
      method: "POST",
      headers: await jsonHeaders(),
      body: JSON.stringify({
        resumeName: resumeName?.value.trim() || uploadData.fileName || "Untitled Resume",
        documentBucket: uploadData.documentBucket,
        documentKey: uploadData.documentKey,
        fileName: uploadData.fileName,
        analysisProvider: selectedProvider()
      })
    });

    const analysisData = await analysisResponse.json();

    if (!analysisResponse.ok) {
      throw new Error(analysisData.error || "PDF analysis save failed");
    }

    renderAnalysis(analysisData);
    setAccordionOpen("resumeResultCard", true);
    await loadHistory();

    if (analysisData.status === "processing" && analysisData.analysisId) {
      result.insertAdjacentHTML(
        "afterbegin",
        `
          <div class="status-banner status-pending">
            PDF uploaded and queued for AI analysis. This page will update automatically when complete.
          </div>
        `
      );

      await pollAnalysisUntilComplete(analysisData.analysisId);
    }

    setButtonSaved(uploadButton, "Complete ✓");
  } catch (error) {
    result.textContent = `Error: ${error.message}`;
    resetButton(uploadButton);
  }
}

async function loadHistory() {
  if (!history && !resumeAnalysisSelect) {
    return;
  }

  if (history) {
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

    if (history) {
      renderResumeHistory();
    }

    applyDefaultResumeAccordionState();

    if (deepLinkAnalysisId) {
      openResumeDetailView();
      await loadAnalysisDetail(deepLinkAnalysisId);
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  } catch (error) {
    if (history) {
      history.textContent = `Error: ${error.message}`;
    }
  }
}

async function pollAnalysisUntilComplete(analysisId, maxAttempts = 30, delayMs = 3000) {
  if (!analysisId) {
    return;
  }

  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    await new Promise(resolve => setTimeout(resolve, delayMs));

    const response = await fetch(`${API_BASE_URL}/analysis/${analysisId}`, {
      headers: await authHeaders()
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Could not refresh analysis detail");
    }

    renderAnalysis(data);
    await loadHistory();

    if (data.status !== "processing") {
      return;
    }
  }

  result.insertAdjacentHTML(
    "afterbegin",
    `
      <div class="status-banner status-pending">
        Analysis is still processing. It is taking longer than expected.
      </div>
    `
  );
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

function renderJobMatch(data, tailoring = null, interviewPrep = null) {
  const matchedKeywords = (data.matchedKeywords || [])
    .map(item => `<li>${escapeHtml(item)}</li>`)
    .join("");

  const missingKeywords = (data.missingKeywords || [])
    .map(item => `<li>${escapeHtml(item)}</li>`)
    .join("");

  const leadershipGaps = (data.leadershipGaps || [])
    .map(item => `<li>${escapeHtml(item)}</li>`)
    .join("");

  const technicalGaps = (data.technicalGaps || [])
    .map(item => `<li>${escapeHtml(item)}</li>`)
    .join("");

  const recommendedChanges = (data.recommendedResumeChanges || [])
    .map(item => `<li>${escapeHtml(item)}</li>`)
    .join("");

  const isCompleted = data.status === "completed";
  const statusClass = isCompleted ? "" : "status-pending";
  const resumePreview = data.resumeText
    ? escapeHtml(data.resumeText.slice(0, 2000))
    : "No resume text available.";

  result.innerHTML = `
    <div class="score-card">
      <div class="score-circle">${escapeHtml(data.matchScore || 0)}</div>
      <div>
        <h3>Job Match Complete</h3>
	<p><strong>Job Name:</strong> ${escapeHtml(data.jobName || "Untitled Job")}</p>
	<p><strong>URL:</strong> ${renderJobUrl(data.jobUrl)}</p>
        <!-- <p><strong>Match ID:</strong> ${escapeHtml(data.matchId)}</p> -->
        <!-- <p><strong>Resume Analysis ID:</strong> ${escapeHtml(data.resumeAnalysisId)}</p> -->
        <p><strong>Resume Analysis:</strong> ${escapeHtml(renderResumeLabelFromJobMatch(data))}</p>
        <p><strong>Created:</strong> ${escapeHtml(formatEastern(data.createdAt))}</p>
      </div>
    </div>

    <div class="metrics">
      <span class="metric ${statusClass}">Status: ${escapeHtml(data.status || "unknown")}</span>
      <span class="metric">Provider: ${escapeHtml(data.provider || "unknown")}</span>
      <span class="metric">Model: ${escapeHtml(data.model || "N/A")}</span>
      <span class="metric">Leadership: ${escapeHtml(data.leadershipMatchScore || 0)}</span>
      <span class="metric">Technical: ${escapeHtml(data.technicalMatchScore || 0)}</span>
      <span class="metric">Architecture: ${escapeHtml(data.architectureMatchScore || 0)}</span>
      <span class="metric">ATS: ${escapeHtml(data.atsKeywordScore || 0)}</span>
      <span class="metric">Duration: ${escapeHtml(data.analysisDurationMs || 0)} ms</span>
    </div>

    ${isCompleted ? `
    <h3>Executive Summary</h3>
    <p>${escapeHtml(data.executiveSummary || "No summary available.")}</p>

    <div class="result-grid">
      <div class="result-box">
        <h3>Matched Keywords</h3>
        <ul>${matchedKeywords}</ul>
      </div>

      <div class="result-box">
        <h3>Missing Keywords</h3>
        <ul>${missingKeywords}</ul>
      </div>

      <div class="result-box">
        <h3>Leadership Gaps</h3>
        <ul>${leadershipGaps}</ul>
      </div>

      <div class="result-box">
        <h3>Technical Gaps</h3>
        <ul>${technicalGaps}</ul>
      </div>

      <div class="result-box">
        <h3>Recommended Resume Changes</h3>
        <ul>${recommendedChanges}</ul>
      </div>
    </div>

    <h3>Resume Text Preview</h3>
    <div class="resume-preview">${resumePreview}</div>

    ${
      data.resumeDocumentBucket && data.resumeDocumentKey
        ? `
          <div class="resume-download-section">
            <button
              class="secondary"
              onclick="downloadResumeDocument('${escapeHtml(data.resumeAnalysisId)}')">
              Download Resume PDF
            </button>
          </div>
        `
        : ""
    }

    ${renderTailoringSection(tailoring)}
    ${renderInterviewPrepSection(interviewPrep)}
  ` : `
    <p><strong>Status:</strong> Job match is still processing. Refresh matches shortly.</p>
  `}
  `;
}

function populateResumeAnalysisSelect(analyses) {
  if (!resumeAnalysisSelect) {
    return;
  }

  const resumeAnalyses = analyses.filter(item =>
    item.status === "completed" &&
    item.analysisId &&
    !item.matchId &&
    item.sourceType
  );

  if (resumeAnalyses.length === 0) {
    resumeAnalysisSelect.innerHTML =
      `<option value="">No completed resume analyses available</option>`;
    return;
  }

  resumeAnalysisSelect.innerHTML = resumeAnalyses.map(item => {
    const label =
      `${item.resumeName || "Untitled Resume"} | ` +
      `${formatEastern(item.createdAt)} | ` +
      `${item.sourceType || "resume"} | ` +
      `score ${item.score || 0} | ` +
      `${item.fileName || "text resume"}`;

    return `<option value="${escapeHtml(item.analysisId)}">${escapeHtml(label)}</option>`;
  }).join("");
}

async function matchJobDescription() {
  const analysisId = resumeAnalysisSelect.value;
  const jdText = jobDescriptionText.value.trim();

  if (!analysisId) {
    result.textContent = "Select a resume analysis first.";
    return;
  }

  if (!jdText) {
    result.textContent = "Paste a job description first.";
    return;
  }

  setButtonLoading(matchJobButton, "Matching...");
  focusAccordionCard("jobResultCard");
  result.textContent = "Matching resume to job description...";

  try {
    const response = await fetch(`${API_BASE_URL}/match-job-description`, {
      method: "POST",
      headers: await jsonHeaders(),
      body: JSON.stringify({
        analysisId: analysisId,
	jobName: jobName.value.trim() || "Untitled Job",
        jobUrl: jobUrl?.value.trim() || "",
        jobDescriptionText: jdText,
        analysisProvider: selectedProvider()
      })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Job match failed");
    }

    renderJobMatch(data, null);
    setAccordionOpen("jobResultCard", true);
    await loadJobMatches();

    if (response.status === 202) {
      result.insertAdjacentHTML(
        "afterbegin",
        `<p><strong>Status:</strong> Job match queued for AI analysis. Refresh matches in a moment to view the completed result.</p>`
      );
    }

    setButtonSaved(matchJobButton, "Queued ✓");
  } catch (error) {
    result.textContent = `Error: ${error.message}`;
    resetButton(matchJobButton);
  }
}

async function loadJobMatches() {
  if (!jobMatches) {
    return;
  }

  jobMatches.textContent = "Loading job matches...";

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
  } catch (error) {
    result.textContent = `Error: ${error.message}`;
  }
}

async function deleteAnalysis(analysisId) {
  if (!confirm("Delete this resume analysis? This cannot be undone.")) {
    return;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/analysis/${analysisId}`, {
      method: "DELETE",
      headers: await authHeaders()
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Delete failed");
    }

    result.textContent = "Resume analysis deleted.";
    await loadHistory();
  } catch (error) {
    result.textContent = `Error: ${error.message}`;
  }
}

async function deleteAllAnalyses() {
  if (!confirm("Delete all resume analyses? This cannot be undone.")) {
    return;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/analyses`, {
      method: "DELETE",
      headers: await authHeaders()
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Delete all failed");
    }

    result.textContent = `Deleted ${data.deleted} resume analyses.`;
    await loadHistory();
  } catch (error) {
    result.textContent = `Error: ${error.message}`;
  }
}

async function deleteJobMatch(matchId) {
  if (!confirm("Delete this job match? This cannot be undone.")) {
    return;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/job-match/${matchId}`, {
      method: "DELETE",
      headers: await authHeaders()
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Delete failed");
    }

    result.textContent = "Job match deleted.";
    await loadJobMatches();
  } catch (error) {
    result.textContent = `Error: ${error.message}`;
  }
}

async function deleteAllJobMatches() {
  if (!confirm("Delete all job matches? This cannot be undone.")) {
    return;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/job-matches`, {
      method: "DELETE",
      headers: await authHeaders()
    });

    const data = await response.json();
    console.log("Delete all job matches response:", data);

    if (!response.ok) {
      throw new Error(data.error || "Delete all failed");
    }

    result.textContent = `Deleted ${data.deleted} job matches.`;
    await loadJobMatches();
  } catch (error) {
    result.textContent = `Error: ${error.message}`;
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

function renderStatusSummary(container, label, items) {
  if (!container) {
    return;
  }

  const counts = countByStatus(items);

  container.innerHTML = `
    <span><strong>${escapeHtml(label)}:</strong> ${escapeHtml(String(counts.total ?? 0))}</span>
    <span>Completed: ${escapeHtml(String(counts.completed ?? 0))}</span>
    <span>Processing: ${escapeHtml(String(counts.processing ?? 0))}</span>
    <span>Failed: ${escapeHtml(String(counts.failed ?? 0))}</span>
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
      const aProcessing = a.status === "processing" ? 0 : 1;
      const bProcessing = b.status === "processing" ? 0 : 1;

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
    const detailsId = `resume-details-${escapeHtml(item.analysisId)}`;
    const resumePreview = item.resumeText
      ? escapeHtml(item.resumeText.slice(0, 800))
      : "No resume text available.";

    return `
      <div class="history-item resume-history-card">
        <div class="resume-history-left">
          <div>
            <span class="badge">${escapeHtml(item.sourceType || "unknown")}</span>
            <span class="badge ${item.status === "completed" ? "" : "status-pending"}">${escapeHtml(item.status || "unknown")}</span>
            <span class="badge">${escapeHtml(item.provider || "unknown")}</span>
          </div>

          <!-- <p><strong>ID:</strong> ${escapeHtml(item.analysisId)}</p> -->
          <p><strong>Resume:</strong> ${escapeHtml(item.resumeName || "Untitled Resume")}</p>
          <p><strong>Created:</strong> ${escapeHtml(formatEastern(item.createdAt))}</p>
          <p><strong>Score:</strong> ${escapeHtml(item.score || 0)}</p>

          <div class="button-row">
            <button class="secondary" onclick="toggleCardDetails('${detailsId}')">Expand</button>
            <button class="secondary" onclick="loadAnalysisDetail('${escapeHtml(item.analysisId)}')">View Details</button>
            ${
              item.documentBucket && item.documentKey
                ? `<button class="secondary" onclick="downloadResumeDocument('${escapeHtml(item.analysisId)}')">Download PDF</button>`
                : ""
            }
            <button class="danger" onclick="deleteAnalysis('${escapeHtml(item.analysisId)}')">Delete</button>
          </div>

          <div id="${detailsId}" class="card-details hidden">
            <p><strong>Words:</strong> ${escapeHtml(item.wordCount || 0)}</p>
            <p><strong>Duration:</strong> ${escapeHtml(item.analysisDurationMs || 0)} ms</p>
            <p><strong>Model:</strong> ${escapeHtml(item.model || "N/A")}</p>
            <p><strong>Version:</strong> ${escapeHtml(item.analysisVersion || "N/A")}</p>
          </div>
        </div>

        <div class="resume-history-right">
          <!-- <h4>Resume Text Preview</h4> -->
          <div class="resume-preview small-preview">${resumePreview}</div>
        </div>
      </div>
    `;
  }).join("");
}

function renderJobMatchHistory() {
  if (!jobMatches) {
    return;
  }

  const searchValue = jobSearchInput?.value.trim().toLowerCase() || "";
  const sortValue = jobSortSelect?.value || "newest";

  let filtered = cachedJobMatches.filter(item => {
    const name = (item.jobName || "Untitled Job").toLowerCase();
    const description = (item.jobDescriptionText || "").toLowerCase();
    return name.includes(searchValue) || description.includes(searchValue);
  });

  filtered = sortItems(filtered, sortValue, "matchScore");

  renderStatusSummary(jobMatchSummary, "Total Matches", cachedJobMatches);

  if (filtered.length === 0) {
    jobMatches.textContent = "No job matches found.";
    return;
  }

  jobMatches.innerHTML = filtered.map(item => {
    const detailsId = `job-details-${escapeHtml(item.matchId)}`;
    const resumePreview = item.resumeText
      ? escapeHtml(item.resumeText.slice(0, 800))
      : "No resume text available.";

    return `
      <div class="history-item job-match-card">
        <div class="job-match-left">
          <div>
            <span class="badge">job match</span>
            <span class="badge ${item.status === "completed" ? "" : "status-pending"}">${escapeHtml(item.status || "unknown")}</span>
            <span class="badge">${escapeHtml(item.provider || "unknown")}</span>
          </div>

          <p><strong>Job:</strong> ${escapeHtml(item.jobName || "Untitled Job")}</p>
          <p><strong>URL:</strong> ${renderJobUrl(item.jobUrl)}</p>
          <p><strong>Created:</strong> ${escapeHtml(formatEastern(item.createdAt))}</p>
          <p><strong>Match Score:</strong> ${escapeHtml(item.matchScore || 0)}</p>

          <div class="button-row">
            <button class="secondary" onclick="toggleCardDetails('${detailsId}')">Expand</button>
            <button class="secondary" onclick="loadJobMatchDetail('${escapeHtml(item.matchId)}')">View Details</button>
            <button class="danger" onclick="deleteJobMatch('${escapeHtml(item.matchId)}')">Delete</button>
          </div>

          <div id="${detailsId}" class="card-details hidden">
            <p><strong>Leadership Match:</strong> ${escapeHtml(item.leadershipMatchScore || 0)}</p>
            <p><strong>Technical Match:</strong> ${escapeHtml(item.technicalMatchScore || 0)}</p>
            <p><strong>Architecture Match:</strong> ${escapeHtml(item.architectureMatchScore || 0)}</p>
            <p><strong>ATS Keyword Score:</strong> ${escapeHtml(item.atsKeywordScore || 0)}</p>
            <p><strong>Duration:</strong> ${escapeHtml(item.analysisDurationMs || 0)} ms</p>
            <p><strong>Model:</strong> ${escapeHtml(item.model || "N/A")}</p>
          </div>
        </div>

        <div class="job-match-right">
          <!-- <h4>Resume Text Preview</h4> -->

          <p><strong>Resume:</strong> ${escapeHtml(item.resumeName || "Untitled Resume")}</p>
          <p>Created: ${escapeHtml(formatEastern(item.resumeCreatedAt))} , Source: ${escapeHtml(item.resumeSourceType || "resume")} , Score: ${escapeHtml(item.resumeScore || 0)}</p>

          <div class="resume-preview small-preview">${resumePreview}</div>

          ${
            item.resumeDocumentBucket && item.resumeDocumentKey
              ? `<button class="secondary" onclick="downloadResumeDocument('${escapeHtml(item.resumeAnalysisId)}')">Download Resume PDF</button>`
              : ""
          }
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

function focusAccordionCard(cardId) {
  setAccordionOpen(cardId, true);

  const card = document.getElementById(cardId);

  if (card) {
    card.scrollIntoView({
      behavior: "smooth",
      block: "start"
    });
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

setupAccordionPersistence();

if (analyzeButton) {
  analyzeButton.addEventListener("click", analyzeTextResume);
}

if (uploadButton) {
  uploadButton.addEventListener("click", uploadPdfResume);
}

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

if (matchJobButton) {
  matchJobButton.addEventListener("click", matchJobDescription);
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
  applyPreferredProviderFromProfile().then(loadHistory);
}

if (page === "job-matching") {
  applyPreferredProviderFromProfile().then(() => {
    loadHistory();
    loadJobMatches();
  });
}
