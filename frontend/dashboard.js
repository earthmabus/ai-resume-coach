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

function renderStats(analyses, matches) {
  const totalResumes = analyses.length;
  const totalMatches = matches.length;
  const completedMatches = matches.filter(item => item.status === "completed").length;
  const processing =
    analyses.filter(item => item.status === "processing").length +
    matches.filter(item => item.status === "processing").length;

  dashboardStats.innerHTML = `
    <div class="stat-card">
      <span class="stat-value">${escapeHtml(totalResumes)}</span>
      <span class="stat-label">Resumes</span>
    </div>

    <div class="stat-card">
      <span class="stat-value">${escapeHtml(totalMatches)}</span>
      <span class="stat-label">Job Matches</span>
    </div>

    <div class="stat-card">
      <span class="stat-value">${escapeHtml(completedMatches)}</span>
      <span class="stat-label">Completed Matches</span>
    </div>

    <div class="stat-card">
      <span class="stat-value">${escapeHtml(processing)}</span>
      <span class="stat-label">Processing</span>
    </div>
  `;
}

function renderActivityList(container, activities, emptyMessage) {
  if (activities.length === 0) {
    container.textContent = emptyMessage;
    return;
  }

  container.innerHTML = activities.map(item => `
    <a class="activity-item" href="${escapeHtml(item.href)}">
      <div>
        <div>
          ${statusBadge(item.status)}
        </div>
        <p><strong>${escapeHtml(item.title)}</strong></p>
        <p>${escapeHtml(item.subtitle)}</p>
      </div>
      <div class="activity-date">${escapeHtml(formatEastern(item.createdAt))}</div>
    </a>
  `).join("");
}

function renderRecentActivity(analyses, matches) {
  const resumeActivities = analyses
    .map(item => ({
      title: item.resumeName || "Untitled Resume",
      subtitle: `${item.sourceType || "resume"} | score ${item.score || 0}`,
      status: item.status || "unknown",
      createdAt: item.createdAt || "",
      href: `./resume-analysis.html?analysisId=${encodeURIComponent(item.analysisId)}`
    }))
    .sort((a, b) => new Date(b.createdAt || 0) - new Date(a.createdAt || 0))
    .slice(0, 5);

  const matchActivities = matches
    .map(item => ({
      title: item.jobName || "Untitled Job",
      subtitle: `${item.resumeName || "Untitled Resume"} | match score ${item.matchScore || 0}`,
      status: item.status || "unknown",
      createdAt: item.createdAt || "",
      href: `./job-matching.html?matchId=${encodeURIComponent(item.matchId)}`
    }))
    .sort((a, b) => new Date(b.createdAt || 0) - new Date(a.createdAt || 0))
    .slice(0, 5);

  renderActivityList(
    recentResumeActivity,
    resumeActivities,
    "No recent resume analysis activity yet."
  );

  renderActivityList(
    recentJobActivity,
    matchActivities,
    "No recent job matching activity yet."
  );
}

async function loadDashboard() {
  recentResumeActivity.textContent = "Loading recent resume activities...";
  recentJobActivity.textContent = "Loading recent job matching activities...";

  try {
    const [analysesResponse, matchesResponse] = await Promise.all([
      fetch(`${API_BASE_URL}/analyses`, {
        headers: await authHeaders()
      }),
      fetch(`${API_BASE_URL}/job-matches`, {
        headers: await authHeaders()
      })
    ]);

    const analysesData = await analysesResponse.json();
    const matchesData = await matchesResponse.json();

    if (!analysesResponse.ok) {
      console.warn("Could not load analyses:", analysesData);
    }

    if (!matchesResponse.ok) {
      console.warn("Could not load job matches:", matchesData);
    }

    const analyses = analysesResponse.ok ? analysesData.analyses || [] : [];
    const matches = matchesResponse.ok ? matchesData.jobMatches || [] : [];

    renderStats(analyses, matches);
    renderRecentActivity(analyses, matches);
  } catch (error) {
    console.error("Dashboard load failed:", error);
    recentResumeActivity.textContent = "There is no recent resume activity.";
    recentJobActivity.textContent = "There is no recent job matching activity.";
  }
}

refreshDashboardButton.addEventListener("click", loadDashboard);

loadDashboard();
