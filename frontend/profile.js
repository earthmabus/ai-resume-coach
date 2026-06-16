requireAuth();

const API_BASE_URL = window.APP_CONFIG.apiEndpoint;

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
    alert(`Error loading profile: ${error.message}`);
  }
}

async function saveProfile() {
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

    alert("Profile saved successfully.");
  } catch (error) {
    alert(`Error saving profile: ${error.message}`);
  }
}

document.getElementById("saveProfileButton").addEventListener("click", saveProfile);

loadProfile();
