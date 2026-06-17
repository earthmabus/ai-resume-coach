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
  "careerGoalSummary"
];

const result = document.getElementById("targetCareerResult");
const targetCareerError = document.getElementById("targetCareerError");
const targetCareerSuccess = document.getElementById("targetCareerSuccess");
const saveButton = document.getElementById("saveTargetCareerButton");
const targetCareerError = document.getElementById("targetCareerError");

function readForm() {
  const payload = {};

  fields.forEach(id => {
    payload[id] = document.getElementById(id).value.trim();
  });

  return payload;
}

function writeForm(data) {
  fields.forEach(id => {
    document.getElementById(id).value = data[id] || "";
  });
}

async function loadTargetCareer() {
  try {
    const response = await fetch(`${API_BASE_URL}/target-career`, {
      headers: await authHeaders()
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Could not load target career");
    }

    writeForm(data);
  } catch (error) {
    showTargetCareerError(error.message || "Unable to load existing target career information");
  }
}

async function saveTargetCareer() {
  clearTargetCareerError();
  targetCareerSuccess.classList.add("hidden");

  const payload = readForm();

  try {
    if (!payload.roleTitle || !payload.industry) {
      throw new Error("Target Role Title and Industry are required.");
    }

    const response = await fetch(`${API_BASE_URL}/target-career`, {
      method: "PUT",
      headers: await jsonHeaders(),
      body: JSON.stringify(payload)
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Could not save target career");
    }

    showSavedState()
  } catch (error) {
    saveButton.disabled = false;
    saveButton.textContent = "Save Target Career";
    showTargetCareerError(error.message || "Unable to save target career.");
  }
}

function showTargetCareerError(message) {
  targetCareerError.textContent = message;
  targetCareerError.classList.remove("hidden");
}

function clearTargetCareerError() {
  targetCareerError.textContent = "";
  targetCareerError.classList.add("hidden");
}

function showSavedState() {
  saveButton.disabled = true;
  saveButton.textContent = "Saved ✓";

  setTimeout(() => {
    saveButton.disabled = false;
    saveButton.textContent = "Save Target Career";
  }, 2000);
}

document.getElementById("saveTargetCareerButton").addEventListener("click", saveTargetCareer);

loadTargetCareer();
