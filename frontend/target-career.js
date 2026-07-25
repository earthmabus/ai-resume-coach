requireAuth();

const API_BASE_URL = window.APP_CONFIG.apiEndpoint;
const fields = [
  "roleTitle",
  "industry",
  "seniorityLevel",
  "workEnvironment",
  "keyResponsibilities",
  "requiredSkills",
  "certifications",
  "physicalRequirements",
  "technicalRequirements",
  "leadershipRequirements",
  "careerGoalSummary",
];

const errorBanner = document.getElementById("targetCareerError");
const noticeBanner = document.getElementById("targetCareerNotice");
const listElement = document.getElementById("targetCareerList");
const loadingElement = document.getElementById("targetCareerLoading");
const emptyElement = document.getElementById("targetCareerEmpty");
const editor = document.getElementById("targetCareerEditor");
const editorTitle = document.getElementById("targetCareerEditorTitle");
const editorDescription = document.getElementById("targetCareerEditorDescription");
const saveButton = document.getElementById("saveTargetCareerButton");

let targetCareers = [];
let editingTargetCareerId = null;
let editingVersion = null;

function getErrorMessage(data, fallback) {
  if (typeof data?.error === "string") return data.error;
  if (typeof data?.error?.message === "string") return data.error.message;
  return fallback;
}

function showError(message) {
  errorBanner.textContent = message;
  errorBanner.classList.remove("hidden");
}

function clearError() {
  errorBanner.textContent = "";
  errorBanner.classList.add("hidden");
}

function showNotice(message) {
  noticeBanner.textContent = message;
  noticeBanner.classList.remove("hidden");
  window.setTimeout(() => noticeBanner.classList.add("hidden"), 3000);
}

function readForm() {
  return Object.fromEntries(
    fields.map((id) => [id, document.getElementById(id).value.trim()]),
  );
}

function writeForm(data = {}) {
  fields.forEach((id) => {
    document.getElementById(id).value = data[id] || "";
  });
}

function escapeHtml(value) {
  const element = document.createElement("div");
  element.textContent = value || "";
  return element.innerHTML;
}

function openCreateEditor() {
  clearError();
  editingTargetCareerId = null;
  editingVersion = null;
  writeForm();
  editorTitle.textContent = "Create Target Career";
  editorDescription.textContent = "Define this career direction. You can update these details later.";
  saveButton.textContent = "Create Target Career";
  editor.classList.remove("hidden");
  editor.scrollIntoView({ behavior: "smooth", block: "start" });
  document.getElementById("roleTitle").focus({ preventScroll: true });
}

function openEditEditor(targetCareerId) {
  const career = targetCareers.find((item) => item.targetCareerId === targetCareerId);
  if (!career) return;

  clearError();
  editingTargetCareerId = career.targetCareerId;
  editingVersion = Number(career.version);
  writeForm(career);
  editorTitle.textContent = "Edit Target Career";
  editorDescription.textContent = `Update ${career.roleTitle}. Changes apply to future uses of this career.`;
  saveButton.textContent = "Save Changes";
  editor.classList.remove("hidden");
  editor.scrollIntoView({ behavior: "smooth", block: "start" });
  document.getElementById("roleTitle").focus({ preventScroll: true });
}

function closeEditor() {
  editor.classList.add("hidden");
  editingTargetCareerId = null;
  editingVersion = null;
  writeForm();
}

function renderTargetCareers() {
  loadingElement.classList.add("hidden");
  listElement.innerHTML = "";
  emptyElement.classList.toggle("hidden", targetCareers.length !== 0);

  targetCareers.forEach((career) => {
    const article = document.createElement("article");
    article.className = "target-career-card";
    article.innerHTML = `
      <div class="target-career-card-header">
        <div>
          <h3>${escapeHtml(career.roleTitle)}</h3>
          <p>${escapeHtml(career.industry)}${career.seniorityLevel ? ` · ${escapeHtml(career.seniorityLevel)}` : ""}</p>
        </div>
        <span class="version-badge">v${Number(career.version || 1)}</span>
      </div>
      ${career.careerGoalSummary ? `<p class="target-career-summary">${escapeHtml(career.careerGoalSummary)}</p>` : ""}
      <dl class="target-career-meta">
        <div><dt class="last-updated-label">Last Updated</dt><dd>${escapeHtml(formatTimestamp(career.updatedAt || career.createdAt))}</dd></div>
      </dl>
      <div class="card-actions">
        <button type="button" class="edit-target-career">Edit</button>
        <button type="button" class="secondary-button delete-target-career">Delete</button>
      </div>
    `;
    article.querySelector(".edit-target-career").addEventListener("click", () => openEditEditor(career.targetCareerId));
    article.querySelector(".delete-target-career").addEventListener("click", () => deleteTargetCareer(career));
    listElement.appendChild(article);
  });
}

function formatTimestamp(value) {
  if (!value) return "Unknown";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

async function loadTargetCareers() {
  clearError();
  loadingElement.classList.remove("hidden");
  try {
    const response = await fetch(`${API_BASE_URL}/target-careers`, { headers: await authHeaders() });
    const data = await response.json();
    if (!response.ok) throw new Error(getErrorMessage(data, "Could not load target careers"));
    targetCareers = Array.isArray(data.targetCareers) ? data.targetCareers : [];
    renderTargetCareers();
  } catch (error) {
    loadingElement.classList.add("hidden");
    showError(error.message || "Unable to load target careers.");
  }
}

async function saveTargetCareer() {
  clearError();
  const payload = readForm();
  if (!payload.roleTitle || !payload.industry) {
    showError("Target Role Title and Industry are required.");
    return;
  }

  const isEditing = Boolean(editingTargetCareerId);
  saveButton.disabled = true;
  saveButton.textContent = isEditing ? "Saving…" : "Creating…";

  try {
    const url = isEditing
      ? `${API_BASE_URL}/target-careers/${encodeURIComponent(editingTargetCareerId)}`
      : `${API_BASE_URL}/target-careers`;
    const response = await fetch(url, {
      method: isEditing ? "PUT" : "POST",
      headers: await jsonHeaders(),
      body: JSON.stringify(isEditing ? { ...payload, version: editingVersion } : payload),
    });
    const data = await response.json();
    if (response.status === 409) {
      await loadTargetCareers();
      throw new Error(getErrorMessage(data, "This target career changed elsewhere. Review the latest version and try again."));
    }
    if (!response.ok) throw new Error(getErrorMessage(data, "Could not save target career"));

    closeEditor();
    await loadTargetCareers();
    showNotice(isEditing ? "Target career updated." : "Target career created.");
  } catch (error) {
    showError(error.message || "Unable to save target career.");
  } finally {
    saveButton.disabled = false;
    saveButton.textContent = editingTargetCareerId ? "Save Changes" : "Create Target Career";
  }
}

async function deleteTargetCareer(career) {
  clearError();
  const confirmed = window.confirm(`Delete “${career.roleTitle}”? This cannot be undone.`);
  if (!confirmed) return;

  try {
    const response = await fetch(
      `${API_BASE_URL}/target-careers/${encodeURIComponent(career.targetCareerId)}`,
      {
        method: "DELETE",
        headers: await jsonHeaders(),
        body: JSON.stringify({ version: Number(career.version) }),
      },
    );
    const data = await response.json();
    if (!response.ok) throw new Error(getErrorMessage(data, "Could not delete target career"));
    if (editingTargetCareerId === career.targetCareerId) closeEditor();
    await loadTargetCareers();
    showNotice("Target career deleted.");
  } catch (error) {
    showError(error.message || "Unable to delete target career.");
  }
}

document.getElementById("createTargetCareerButton").addEventListener("click", openCreateEditor);
document.getElementById("emptyCreateTargetCareerButton").addEventListener("click", openCreateEditor);
document.getElementById("refreshTargetCareersButton").addEventListener("click", loadTargetCareers);
document.getElementById("cancelTargetCareerButtonBottom").addEventListener("click", closeEditor);
saveButton.addEventListener("click", saveTargetCareer);

loadTargetCareers();
