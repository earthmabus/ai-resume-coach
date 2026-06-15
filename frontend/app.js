const API_BASE_URL = window.APP_CONFIG?.apiEndpoint;

if (!API_BASE_URL) {
  throw new Error("Missing API endpoint configuration");
}

const analyzeButton = document.getElementById("analyzeButton");
const uploadButton = document.getElementById("uploadButton");
const refreshHistoryButton = document.getElementById("refreshHistoryButton");

const textarea = document.getElementById("resumeText");
const fileInput = document.getElementById("resumeFile");
const result = document.getElementById("result");
const history = document.getElementById("history");

const textTab = document.getElementById("textTab");
const pdfTab = document.getElementById("pdfTab");
const textPanel = document.getElementById("textPanel");
const pdfPanel = document.getElementById("pdfPanel");
const providerSelect = document.getElementById("analysisProvider");

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
        documentBucket: uploadData.documentBucket,
        documentKey: uploadData.documentKey,
        fileName: uploadData.fileName,
        analysisProvider: selectedProvider()
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
        fileName: uploadData.fileName
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
  history.textContent = "Loading history...";

  try {
    const response = await fetch(`${API_BASE_URL}/analyses`);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Could not load history");
    }

    const analyses = data.analyses || [];

    if (analyses.length === 0) {
      history.textContent = "No analyses found.";
      return;
    }

    history.innerHTML = analyses.map(item => `
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
        <button onclick="loadAnalysisDetail('${escapeHtml(item.analysisId)}')">View Details</button>
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
  return providerSelect.value;
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

analyzeButton.addEventListener("click", analyzeTextResume);
uploadButton.addEventListener("click", uploadPdfResume);
refreshHistoryButton.addEventListener("click", loadHistory);

textTab.addEventListener("click", () => showPanel("text"));
pdfTab.addEventListener("click", () => showPanel("pdf"));

loadHistory();
