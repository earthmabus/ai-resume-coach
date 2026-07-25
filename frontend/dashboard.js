requireAuth();

const API_BASE_URL = window.APP_CONFIG.apiEndpoint;

const dashboardStats = document.getElementById("dashboardStats");
const recentResumeActivity = document.getElementById("recentResumeActivity");
const recentJobActivity = document.getElementById("recentJobActivity");
const refreshDashboardButton = document.getElementById("refreshDashboardButton");

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
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

function statusBadge(status) {
  const statusClass = status === "completed" ? "" : "status-pending";
  return `<span class="badge ${statusClass}">${escapeHtml(status || "unknown")}</span>`;
}

function renderStats(targetCareers, analyses, matches) {
  const totalTargetCareers = targetCareers.length;
  const totalResumes = analyses.length;
  const totalMatches = matches.length;
  const processing =
    analyses.filter(item => item.status === "processing").length +
    matches.filter(item => item.status === "processing").length;

  dashboardStats.innerHTML = `
    <div class="stat-card">
      <span class="stat-value">${escapeHtml(totalTargetCareers)}</span>
      <span class="stat-label">Target Careers</span>
    </div>

    <div class="stat-card">
      <span class="stat-value">${escapeHtml(totalResumes)}</span>
      <span class="stat-label">Resumes</span>
    </div>

    <div class="stat-card">
      <span class="stat-value">${escapeHtml(totalMatches)}</span>
      <span class="stat-label">Job Matches</span>
    </div>


    <div class="stat-card">
      <span class="stat-value">${escapeHtml(processing)}</span>
      <span class="stat-label">Processing</span>
    </div>
  `;
}

function scoreToneClass(score) {
  const numericScore = Number(score) || 0;
  if (numericScore >= 80) return "score-good";
  if (numericScore >= 70) return "score-warning";
  return "score-poor";
}

function targetCareerFromAnalysis(item) {
  return item.targetCareer || item.targetCareerSnapshot || {};
}

function targetCareerVersion(item) {
  const career = targetCareerFromAnalysis(item);
  return `v${Number(career.version ?? item.targetCareerVersion ?? 1) || 1}`;
}

function renderResumeActivity(item) {
  const career = targetCareerFromAnalysis(item);
  const roleTitle = career.roleTitle || item.targetRoleTitle || "Target Career unavailable";
  const score = Number(item.score) || 0;
  const fileName = item.fileName || "";
  return `
    <a class="dashboard-history-item" href="./resume-analysis.html?analysisId=${encodeURIComponent(item.analysisId)}">
      <div class="dashboard-score-circle ${scoreToneClass(score)}" aria-label="ATS score ${escapeHtml(score)}">${escapeHtml(score)}</div>
      <div class="dashboard-context-grid">
        <div class="analysis-context-panel">
          <span class="analysis-context-label">Target Career</span>
          <strong>${escapeHtml(roleTitle)} <span class="analysis-context-version">${escapeHtml(targetCareerVersion(item))}</span></strong>
        </div>
        <div class="analysis-context-panel">
          <span class="analysis-context-label">Resume</span>
          <strong>${escapeHtml(item.resumeName || "Untitled Resume")}</strong>
          ${fileName ? `<span class="analysis-context-file">${escapeHtml(fileName)}</span>` : ""}
        </div>
      </div>
      <div class="dashboard-history-metrics">
        ${statusBadge(item.status)}
        <span class="metric">Created: ${escapeHtml(formatEastern(item.createdAt))}</span>
        <span class="metric">Provider: ${escapeHtml(item.provider || "unknown")}</span>
        <span class="metric">Model: ${escapeHtml(item.model || "N/A")}</span>
        <span class="metric">Words: ${escapeHtml(item.wordCount || 0)}</span>
      </div>
    </a>
  `;
}

function renderJobActivity(item) {
  const score = Number(item.matchScore) || 0;
  return `
    <a class="dashboard-history-item" href="./job-matching.html?matchId=${encodeURIComponent(item.matchId)}">
      <div class="dashboard-score-circle ${scoreToneClass(score)}" aria-label="Match score ${escapeHtml(score)}">${escapeHtml(score)}</div>
      <div class="dashboard-context-grid">
        <div class="analysis-context-panel">
          <span class="analysis-context-label">Job</span>
          <strong>${escapeHtml(item.jobName || "Untitled Job")}</strong>
          ${item.jobUrl ? `<span class="analysis-context-file">${escapeHtml(item.jobUrl)}</span>` : ""}
        </div>
        <div class="analysis-context-panel">
          <span class="analysis-context-label">Resume</span>
          <strong>${escapeHtml(item.resumeName || "Untitled Resume")}</strong>
          ${item.resumeFileName ? `<span class="analysis-context-file">${escapeHtml(item.resumeFileName)}</span>` : ""}
        </div>
      </div>
      <div class="dashboard-history-metrics">
        ${statusBadge(item.status)}
        <span class="metric">Provider: ${escapeHtml(item.provider || "unknown")}</span>
        <span class="metric">Leadership: ${escapeHtml(item.leadershipMatchScore || 0)}</span>
        <span class="metric">Technical: ${escapeHtml(item.technicalMatchScore || 0)}</span>
        <span class="metric">Architecture: ${escapeHtml(item.architectureMatchScore || 0)}</span>
        <span class="metric">ATS: ${escapeHtml(item.atsKeywordScore || 0)}</span>
      </div>
    </a>
  `;
}

function renderRecentActivity(analyses, matches) {
  const recentAnalyses = [...analyses]
    .sort((a, b) => new Date(b.createdAt || 0) - new Date(a.createdAt || 0))
    .slice(0, 5);
  const recentMatches = [...matches]
    .sort((a, b) => new Date(b.createdAt || 0) - new Date(a.createdAt || 0))
    .slice(0, 5);

  recentResumeActivity.innerHTML = recentAnalyses.length
    ? recentAnalyses.map(renderResumeActivity).join("")
    : "No recent resume analysis activity yet.";

  recentJobActivity.innerHTML = recentMatches.length
    ? recentMatches.map(renderJobActivity).join("")
    : "No recent job matching activity yet.";
}

async function loadDashboard() {
  recentResumeActivity.textContent = "Loading recent resume activities...";
  recentJobActivity.textContent = "Loading recent job matching activities...";

  try {
    const [targetCareersResponse, analysesResponse, matchesResponse] = await Promise.all([
      fetch(`${API_BASE_URL}/target-careers`, {
        headers: await authHeaders()
      }),
      fetch(`${API_BASE_URL}/analyses`, {
        headers: await authHeaders()
      }),
      fetch(`${API_BASE_URL}/job-matches`, {
        headers: await authHeaders()
      })
    ]);

    const targetCareersData = await targetCareersResponse.json();
    const analysesData = await analysesResponse.json();
    const matchesData = await matchesResponse.json();

    if (!targetCareersResponse.ok) {
      console.warn("Could not load target careers:", targetCareersData);
    }

    if (!analysesResponse.ok) {
      console.warn("Could not load analyses:", analysesData);
    }

    if (!matchesResponse.ok) {
      console.warn("Could not load job matches:", matchesData);
    }

    const targetCareers = targetCareersResponse.ok ? targetCareersData.targetCareers || [] : [];
    const analyses = analysesResponse.ok ? analysesData.analyses || [] : [];
    const matches = matchesResponse.ok ? matchesData.jobMatches || [] : [];

    renderStats(targetCareers, analyses, matches);
    renderRecentActivity(analyses, matches);
  } catch (error) {
    console.error("Dashboard load failed:", error);
    recentResumeActivity.textContent = "There is no recent resume activity.";
    recentJobActivity.textContent = "There is no recent job matching activity.";
  }
}

refreshDashboardButton.addEventListener("click", loadDashboard);

loadDashboard();
