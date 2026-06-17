requireAuth();

const API_BASE_URL = window.APP_CONFIG.apiEndpoint;

const saveProfileButton = document.getElementById("saveProfileButton");
const profileError = document.getElementById("profileError");

function showProfileError(message) {
  profileError.textContent = message;
  profileError.classList.remove("hidden");
}

function clearProfileError() {
  profileError.textContent = "";
  profileError.classList.add("hidden");
}

function showProfileSavedState() {
  saveProfileButton.disabled = true;
  saveProfileButton.textContent = "Saved ✓";

  setTimeout(() => {
    saveProfileButton.disabled = false;
    saveProfileButton.textContent = "Save Profile";
  }, 2000);
}

async function loadProfile() {
  try {
    const response = await fetch(`${API_BASE_URL}/profile`, {
      headers: await authHeaders()
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Could not load profile");
    }

    document.getElementById("profileName").value = data.name || "";
    document.getElementById("currentTitle").value = data.currentTitle || "";
    document.getElementById("targetTitle").value = data.targetTitle || "";
    document.getElementById("yearsExperience").value = data.yearsExperience || "";
    document.getElementById("certifications").value = data.certifications || "";
    document.getElementById("preferredProvider").value = data.preferredProvider || "openai";
    document.getElementById("resumeStyle").value = data.resumeStyle || "executive";
  } catch (error) {
    showProfileError(error.message || "Unable to load profile.");
  }
}

async function saveProfile() {
  clearProfileError();

  saveProfileButton.disabled = true;
  saveProfileButton.textContent = "Saving...";

  try {
    const response = await fetch(`${API_BASE_URL}/profile`, {
      method: "PUT",
      headers: await jsonHeaders(),
      body: JSON.stringify({
        name: document.getElementById("profileName").value,
        currentTitle: document.getElementById("currentTitle").value,
        targetTitle: document.getElementById("targetTitle").value,
        yearsExperience: document.getElementById("yearsExperience").value,
        certifications: document.getElementById("certifications").value,
        preferredProvider: document.getElementById("preferredProvider").value,
        resumeStyle: document.getElementById("resumeStyle").value
      })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Could not save profile");
    }

    showProfileSavedState();
  } catch (error) {
    saveProfileButton.disabled = false;
    saveProfileButton.textContent = "Save Profile";

    showProfileError(error.message || "Unable to save profile.");
  }
}

document.getElementById("saveProfileButton").addEventListener("click", saveProfile);

loadProfile();
