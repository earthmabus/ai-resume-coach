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

    if (data.roleTitle) {
      result.textContent = `Loaded target career: ${data.roleTitle}`;
    }
  } catch (error) {
    result.textContent = `Error: ${error.message}`;
  }
}

async function saveTargetCareer() {
  const payload = readForm();

  if (!payload.roleTitle || !payload.industry) {
    result.textContent = "Target Role Title and Industry are required.";
    return;
  }

  result.textContent = "Saving target career...";

  try {
    const response = await fetch(`${API_BASE_URL}/target-career`, {
      method: "PUT",
      headers: await jsonHeaders(),
      body: JSON.stringify(payload)
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Could not save target career");
    }

    result.textContent = `Saved target career: ${data.roleTitle}`;
  } catch (error) {
    result.textContent = `Error: ${error.message}`;
  }
}

document.getElementById("saveTargetCareerButton").addEventListener("click", saveTargetCareer);

loadTargetCareer();
