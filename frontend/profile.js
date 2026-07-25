requireAuth();

const API_BASE_URL = window.APP_CONFIG.apiEndpoint;

const saveProfileButton = document.getElementById("saveProfileButton");
const profileError = document.getElementById("profileError");
const firstNameInput = document.getElementById("firstName");
const lastNameInput = document.getElementById("lastName");
const emailAddressInput = document.getElementById("emailAddress");
const preferredProviderSelect = document.getElementById("preferredProvider");

let profileVersion = 0;

function getErrorMessage(data, fallback) {
  if (typeof data?.error === "string") {
    return data.error;
  }

  if (typeof data?.error?.message === "string") {
    return data.error.message;
  }

  return fallback;
}

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

async function getAuthenticatedCognitoUser() {
  // CognitoIdentityServiceProvider operations such as getUserAttributes and
  // updateAttributes require the current CognitoUser to have a valid session
  // attached. Loading a page reconstructs the user from local storage, but the
  // session is not attached until getSession completes.
  await getCurrentSession();

  const user = getCurrentUser();

  if (!user) {
    throw new Error("No current user");
  }

  return user;
}

async function getCognitoAttributes() {
  const user = await getAuthenticatedCognitoUser();

  return new Promise((resolve, reject) => {
    user.getUserAttributes((error, attributes) => {
      if (error) {
        reject(error);
        return;
      }

      const values = Object.fromEntries(
        (attributes || []).map((attribute) => [
          attribute.getName(),
          attribute.getValue(),
        ]),
      );

      resolve(values);
    });
  });
}

async function updateCognitoNameAttributes() {
  const user = await getAuthenticatedCognitoUser();

  const attributes = [
    new AmazonCognitoIdentity.CognitoUserAttribute({
      Name: "given_name",
      Value: firstNameInput.value.trim(),
    }),
    new AmazonCognitoIdentity.CognitoUserAttribute({
      Name: "family_name",
      Value: lastNameInput.value.trim(),
    }),
  ];

  return new Promise((resolve, reject) => {
    user.updateAttributes(attributes, (error, result) => {
      if (error) {
        reject(error);
        return;
      }

      resolve(result);
    });
  });
}

async function loadProfile() {
  clearProfileError();

  try {
    const [attributes, response] = await Promise.all([
      getCognitoAttributes(),
      fetch(`${API_BASE_URL}/profile`, {
        headers: await authHeaders(),
      }),
    ]);

    const data = await response.json();

    if (!response.ok) {
      throw new Error(
        getErrorMessage(data, "Could not load profile"),
      );
    }

    profileVersion = Number(data.version ?? 0);
    firstNameInput.value = attributes.given_name || "";
    lastNameInput.value = attributes.family_name || "";
    emailAddressInput.value = attributes.email || "";
    preferredProviderSelect.value = data.preferredProvider || "openai";
  } catch (error) {
    showProfileError(error.message || "Unable to load profile.");
  }
}

async function saveProfile() {
  clearProfileError();

  saveProfileButton.disabled = true;
  saveProfileButton.textContent = "Saving...";

  try {
    await updateCognitoNameAttributes();

    const response = await fetch(`${API_BASE_URL}/profile`, {
      method: "PUT",
      headers: await jsonHeaders(),
      body: JSON.stringify({
        version: profileVersion,
        preferredProvider: preferredProviderSelect.value,
      }),
    });

    const data = await response.json();

    if (response.status === 409) {
      await loadProfile();

      throw new Error(
        getErrorMessage(
          data,
          (
            "Your profile was changed elsewhere. "
            + "The latest version has been loaded. "
            + "Review it and try again."
          ),
        ),
      );
    }

    if (!response.ok) {
      throw new Error(
        getErrorMessage(data, "Could not save profile"),
      );
    }

    profileVersion = Number(data.version);
    showProfileSavedState();
  } catch (error) {
    saveProfileButton.disabled = false;
    saveProfileButton.textContent = "Save Profile";
    showProfileError(error.message || "Unable to save profile.");
  }
}

saveProfileButton.addEventListener("click", saveProfile);
loadProfile();
