const API_BASE_URL = "https://7fyb8rvs84.execute-api.us-east-1.amazonaws.com";

const analyzeButton = document.getElementById("analyzeButton");
const uploadButton = document.getElementById("uploadButton");
const refreshHistoryButton = document.getElementById("refreshHistoryButton");

const textarea = document.getElementById("resumeText");
const fileInput = document.getElementById("resumeFile");
const result = document.getElementById("result");
const history = document.getElementById("history");

function renderAnalysis(data) {
  const strengths = (data.strengths || []).map(item => `<li>${item}</li>`).join("");
  const recommendations = (data.recommendations || []).map(item => `<li>${item}</li>`).join("");

  result.innerHTML = `
    <div>
      <span class="badge">${data.sourceType || "text"}</span>
      <span class="badge">${data.status || "completed"}</span>
      <span class="badge">${data.analysisVersion || "unknown"}</span>
    </div>

    <p><strong>Analysis ID:</strong> ${data.analysisId}</p>
    <p><strong>Created:</strong> ${data.createdAt}</p>
    <p><strong>File:</strong> ${data.fileName || "N/A"}</p>

    <div class="score">${data.score || data.overallScore || 0}</div>

    <h3>Strengths</h3>
    <ul>${strengths}</ul>

    <h3>Recommendations</h3>
    <ul>${recommendations}</ul>
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
        resumeText: textarea.value
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
        fileName: uploadData.fileName
      })
    });

    const analysisData = await analysisResponse.json();

    if (!analysisResponse.ok) {
      throw new Error(analysisData.error || "PDF analysis save failed");
    }

    renderAnalysis(analysisData);
    await loadHistory();
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
          <span class="badge">${item.sourceType || "unknown"}</span>
          <span class="badge">${item.status || "unknown"}</span>
        </div>
        <p><strong>ID:</strong> ${item.analysisId}</p>
        <p><strong>Created:</strong> ${item.createdAt}</p>
        <p><strong>Score:</strong> ${item.score || 0}</p>
        <p><strong>File:</strong> ${item.fileName || "N/A"}</p>
        <button onclick="loadAnalysisDetail('${item.analysisId}')">View Details</button>
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

analyzeButton.addEventListener("click", analyzeTextResume);
uploadButton.addEventListener("click", uploadPdfResume);
refreshHistoryButton.addEventListener("click", loadHistory);

loadHistory();
