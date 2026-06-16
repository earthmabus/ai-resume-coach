requireAuth();

const API_BASE_URL = window.APP_CONFIG.apiEndpoint;
const profileResult = document.getElementById("profileResult");

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

    profileResult.textContent = "Profile loaded.";
  } catch (error) {
    profileResult.textContent = `Error: ${error.message}`;
  }
}

async function saveProfile() {
  profileResult.textContent = "Saving profile...";

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

    profileResult.textContent = `Profile saved at ${new Date().toLocaleString()}.`;
  } catch (error) {
    profileResult.textContent = `Error: ${error.message}`;
  }
}

document.getElementById("saveProfileButton").addEventListener("click", saveProfile);

loadProfile();
