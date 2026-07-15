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

const targetCareerError =
  document.getElementById("targetCareerError");

const saveButton =
  document.getElementById(
    "saveTargetCareerButton",
  );

let targetCareerVersion = 0;


function getErrorMessage(data, fallback) {
  if (typeof data?.error === "string") {
    return data.error;
  }

  if (typeof data?.error?.message === "string") {
    return data.error.message;
  }

  return fallback;
}


function readForm() {
  const payload = {};

  fields.forEach((id) => {
    payload[id] =
      document.getElementById(id).value.trim();
  });

  return payload;
}


function writeForm(data) {
  fields.forEach((id) => {
    document.getElementById(id).value =
      data[id] || "";
  });
}


function showTargetCareerError(message) {
  targetCareerError.textContent = message;
  targetCareerError.classList.remove("hidden");
}


function clearTargetCareerError() {
  targetCareerError.textContent = "";
  targetCareerError.classList.add("hidden");
}


function setSaveButtonIdle() {
  saveButton.disabled = false;
  saveButton.textContent = "Save Target Career";
}


function showSavedState() {
  saveButton.disabled = true;
  saveButton.textContent = "Saved ✓";

  setTimeout(() => {
    setSaveButtonIdle();
  }, 2000);
}


async function loadTargetCareer() {
  clearTargetCareerError();

  try {
    const response = await fetch(
      `${API_BASE_URL}/target-career`,
      {
        headers: await authHeaders(),
      },
    );

    const data = await response.json();

    if (!response.ok) {
      throw new Error(
        getErrorMessage(
          data,
          "Could not load target career",
        ),
      );
    }

    targetCareerVersion =
      Number(data.version ?? 0);

    writeForm(data);
  } catch (error) {
    showTargetCareerError(
      error.message
      || (
        "Unable to load existing "
        + "target career information."
      ),
    );
  }
}


async function saveTargetCareer() {
  clearTargetCareerError();

  const payload = readForm();

  if (!payload.roleTitle || !payload.industry) {
    showTargetCareerError(
      "Target Role Title and Industry are required.",
    );
    return;
  }

  saveButton.disabled = true;
  saveButton.textContent = "Saving...";

  try {
    const response = await fetch(
      `${API_BASE_URL}/target-career`,
      {
        method: "PUT",
        headers: await jsonHeaders(),
        body: JSON.stringify({
          ...payload,
          version: targetCareerVersion,
        }),
      },
    );

    const data = await response.json();

    if (response.status === 409) {
      await loadTargetCareer();

      throw new Error(
        getErrorMessage(
          data,
          (
            "Your target career was changed elsewhere. "
            + "The latest version has been loaded. "
            + "Review it and try again."
          ),
        ),
      );
    }

    if (!response.ok) {
      throw new Error(
        getErrorMessage(
          data,
          "Could not save target career",
        ),
      );
    }

    targetCareerVersion =
      Number(data.version);

    writeForm(data);
    showSavedState();
  } catch (error) {
    setSaveButtonIdle();

    showTargetCareerError(
      error.message
      || "Unable to save target career.",
    );
  }
}


saveButton.addEventListener(
  "click",
  saveTargetCareer,
);

loadTargetCareer();
