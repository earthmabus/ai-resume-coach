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
const jobDescriptionText = document.getElementById("jobDescriptionText");
const jobMatches = document.getElementById("jobMatches");

function escapeHtml(value) {
  return String(value || "")
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

  result.innerHTML = `
    <div class="score-card">
      <div class="score-circle">${score}</div>
      <div>
        <h3>Resume Analysis Complete</h3>
        <p><strong>Analysis ID:</strong> ${escapeHtml(data.analysisId)}</p>
        <p><strong>Created:</strong> ${escapeHtml(data.createdAt)}</p>
        <p><strong>File:</strong> ${escapeHtml(data.fileName || "N/A")}</p>
      </div>
    </div>

    <div class="metrics">
      <span class="metric">Leadership: ${escapeHtml(data.leadershipScore || 0)}</span>
      <span class="metric">Technical: ${escapeHtml(data.technicalScore || 0)}</span>
      <span class="metric">Architecture: ${escapeHtml(data.architectureScore || 0)}</span>
      <span class="metric">ATS: ${escapeHtml(data.atsScore || 0)}</span>
      <span class="metric">Model: ${escapeHtml(data.model || "N/A")}</span>
      <span class="metric">Source: ${escapeHtml(data.sourceType || "text")}</span>
      <span class="metric">Status: ${escapeHtml(data.status || "completed")}</span>
      <span class="metric">Provider: ${escapeHtml(data.provider || "rule-based")}</span>
      <span class="metric">Version: ${escapeHtml(data.analysisVersion || "unknown")}</span>
      <span class="metric">Words: ${escapeHtml(data.wordCount || 0)}</span>
      <span class="metric">Duration: ${escapeHtml(data.analysisDurationMs || 0)} ms</span>
    </div>

    <h3>Executive Summary</h3>
    <p>${escapeHtml(data.executiveSummary || "No executive summary available.")}</p>

    <div class="result-grid">
      <div class="result-box">
        <h3>Leadership Gaps</h3>
        <ul>${leadershipGaps}</ul>
      </div>

      <div class="result-box">
        <h3>Technical Gaps</h3>
        <ul>${technicalGaps}</ul>
      </div>
    </div>

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
  `;
}

async function analyzeTextResume() {
  result.textContent = "Analyzing resume text...";

  try {
    const response = await fetch(`${API_BASE_URL}/analyze-resume`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },

      body: JSON.stringify({
        resumeText: textarea.value,
        analysisProvider: selectedProvider()
      })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Text analysis failed");
    }

    renderAnalysis(data);
    await loadHistory();
  } catch (error) {
    result.textContent = `Error: ${error.message}`;
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

  result.textContent = "Requesting upload URL...";

  try {
    const uploadUrlResponse = await fetch(`${API_BASE_URL}/resume-upload-url`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
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
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
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
    await loadHistory();

    if (analysisResponse.status === 202) {
      result.insertAdjacentHTML(
        "afterbegin",
        `<p><strong>Status:</strong> PDF uploaded and queued for AI analysis. Refresh history in a moment to view the completed result.</p>`
      );
    }
  } catch (error) {
    result.textContent = `Error: ${error.message}`;
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
    const response = await fetch(`${API_BASE_URL}/analyses`);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Could not load history");
    }

    const analyses = data.analyses || [];
    const resumeAnalyses = analyses.filter(item =>
      item.status === "completed" &&
      item.analysisId &&
      !item.matchId &&
      item.sourceType
    );

    populateResumeAnalysisSelect(resumeAnalyses);

    if (resumeAnalyses.length === 0) {
      history.textContent = "No resume analyses found.";
      populateResumeAnalysisSelect([]);
      return;
    }

    history.innerHTML = resumeAnalyses.map(item => `
      <div class="history-item">
        <div>
          <span class="badge">${escapeHtml(item.sourceType || "unknown")}</span>
          <span class="badge">${escapeHtml(item.status || "unknown")}</span>
          <span class="badge">${escapeHtml(item.provider || "rule-based")}</span>
        </div>
        <p><strong>ID:</strong> ${escapeHtml(item.analysisId)}</p>
        <p><strong>Created:</strong> ${escapeHtml(item.createdAt)}</p>
        <p><strong>Score:</strong> ${escapeHtml(item.score || 0)}</p>
        <p><strong>Words:</strong> ${escapeHtml(item.wordCount || 0)}</p>
        <p><strong>Duration:</strong> ${escapeHtml(item.analysisDurationMs || 0)} ms</p>
        <p><strong>File:</strong> ${escapeHtml(item.fileName || "N/A")}</p>

	<div class="button-row">
          <button class="secondary" onclick="loadAnalysisDetail('${escapeHtml(item.analysisId)}')">View Details</button>
          <button class="danger" onclick="deleteAnalysis('${escapeHtml(item.analysisId)}')">Delete</button>
        </div>
      </div>
    `).join("");
  } catch (error) {
    history.textContent = `Error: ${error.message}`;
  }
}

async function loadAnalysisDetail(analysisId) {
  result.textContent = "Loading analysis detail...";

  try {
    const response = await fetch(`${API_BASE_URL}/analysis/${analysisId}`);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Could not load analysis detail");
    }

    renderAnalysis(data);
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

function renderJobMatch(data) {
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

  result.innerHTML = `
    <div class="score-card">
      <div class="score-circle">${escapeHtml(data.matchScore || 0)}</div>
      <div>
        <h3>Job Match Complete</h3>
	<p><strong>Job Name:</strong> ${escapeHtml(data.jobName || "Untitled Job")}</p>
        <p><strong>Match ID:</strong> ${escapeHtml(data.matchId)}</p>
        <p><strong>Resume Analysis ID:</strong> ${escapeHtml(data.resumeAnalysisId)}</p>
        <p><strong>Created:</strong> ${escapeHtml(data.createdAt)}</p>
      </div>
    </div>

    <div class="metrics">
      <span class="metric">Provider: ${escapeHtml(data.provider || "unknown")}</span>
      <span class="metric">Model: ${escapeHtml(data.model || "N/A")}</span>
      <span class="metric">Leadership: ${escapeHtml(data.leadershipMatchScore || 0)}</span>
      <span class="metric">Technical: ${escapeHtml(data.technicalMatchScore || 0)}</span>
      <span class="metric">Architecture: ${escapeHtml(data.architectureMatchScore || 0)}</span>
      <span class="metric">ATS: ${escapeHtml(data.atsKeywordScore || 0)}</span>
      <span class="metric">Duration: ${escapeHtml(data.analysisDurationMs || 0)} ms</span>
    </div>

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
    </div>

    <div class="result-grid">
      <div class="result-box">
        <h3>Leadership Gaps</h3>
        <ul>${leadershipGaps}</ul>
      </div>

      <div class="result-box">
        <h3>Technical Gaps</h3>
        <ul>${technicalGaps}</ul>
      </div>
    </div>

    <div class="result-box">
      <h3>Recommended Resume Changes</h3>
      <ul>${recommendedChanges}</ul>
    </div>
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
      `${item.createdAt || "unknown date"} | ` +
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

  result.textContent = "Matching resume to job description...";

  try {
    const response = await fetch(`${API_BASE_URL}/match-job-description`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        analysisId: analysisId,
	jobName: jobName.value.trim() || "Untitled Job",
        jobDescriptionText: jdText,
        analysisProvider: selectedProvider()
      })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Job match failed");
    }

    renderJobMatch(data);
    await loadJobMatches();

    if (response.status === 202) {
      result.insertAdjacentHTML(
        "afterbegin",
        `<p><strong>Status:</strong> Job match queued for AI analysis. Refresh matches in a moment to view the completed result.</p>`
      );
    }
  } catch (error) {
    result.textContent = `Error: ${error.message}`;
  }
}

async function loadJobMatches() {
  if (!jobMatches) {
    return;
  }

  jobMatches.textContent = "Loading job matches...";

  try {
    const response = await fetch(`${API_BASE_URL}/job-matches`);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Could not load job matches");
    }

    const matches = data.jobMatches || [];

    if (matches.length === 0) {
      jobMatches.textContent = "No job matches found.";
      return;
    }

    jobMatches.innerHTML = matches.map(item => `
      <div class="history-item">
        <div>
          <span class="badge">job match</span>
	  <span class="badge">${escapeHtml(item.status || "unknown")}</span>
          <span class="badge">${escapeHtml(item.provider || "unknown")}</span>
        </div>
	<p><strong>Job:</strong> ${escapeHtml(item.jobName || "Untitled Job")}</p>
        <p><strong>ID:</strong> ${escapeHtml(item.matchId)}</p>
        <p><strong>Created:</strong> ${escapeHtml(item.createdAt)}</p>
        <p><strong>Match Score:</strong> ${escapeHtml(item.matchScore || 0)}</p>
	<div class="button-row">
          <button class="secondary" onclick="loadJobMatchDetail('${escapeHtml(item.matchId)}')">View Details</button>
          <button class="danger" onclick="deleteJobMatch('${escapeHtml(item.matchId)}')">Delete</button>
        </div>
      </div>
    `).join("");
  } catch (error) {
    jobMatches.textContent = `Error: ${error.message}`;
  }
}

async function loadJobMatchDetail(matchId) {
  result.textContent = "Loading job match detail...";

  try {
    const response = await fetch(`${API_BASE_URL}/job-match/${matchId}`);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Could not load job match detail");
    }

    renderJobMatch(data);
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
      method: "DELETE"
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
      method: "DELETE"
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
      method: "DELETE"
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
      method: "DELETE"
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Delete all failed");
    }

    result.textContent = `Deleted ${data.deleted} job matches.`;
    await loadJobMatches();
  } catch (error) {
    result.textContent = `Error: ${error.message}`;
  }
}

if (analyzeButton) {
  analyzeButton.addEventListener("click", analyzeTextResume);
}

if (uploadButton) {
  uploadButton.addEventListener("click", uploadPdfResume);
}

if (refreshHistoryButton) {
  refreshHistoryButton.addEventListener("click", loadHistory);
}

if (deleteAllAnalysesButton) {
  deleteAllAnalysesButton.addEventListener("click", deleteAllAnalyses);
}

if (matchJobButton) {
  matchJobButton.addEventListener("click", matchJobDescription);
}

if (refreshJobMatchesButton) {
  refreshJobMatchesButton.addEventListener("click", loadJobMatches);
}

if (deleteAllJobMatchesButton) {
  deleteAllJobMatchesButton.addEventListener("click", deleteAllJobMatches);
}

if (textTab) {
  textTab.addEventListener("click", () => showPanel("text"));
}

if (pdfTab) {
  pdfTab.addEventListener("click", () => showPanel("pdf"));
}

if (page === "resume-analysis") {
  loadHistory();
}

if (page === "job-matching") {
  loadHistory();
  loadJobMatches();
}

