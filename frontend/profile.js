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

async function getAuthenticatedCognitoContext() {
  const session = await getCurrentSession();
  const user = getCurrentUser();

  if (!user) {
    throw new Error("No current user");
  }

  // Explicitly attach the restored session to the reconstructed CognitoUser.
  // This is required by getUserAttributes/updateAttributes in some browser
  // restore paths even though getSession has already validated the tokens.
  user.setSignInUserSession(session);

  return { user, session };
}

function claimsFromSession(session) {
  return session?.getIdToken?.().payload || {};
}

async function getCognitoAttributes(context) {
  const { user } = context;

  return new Promise((resolve, reject) => {
    user.getUserAttributes((error, attributes) => {
      if (error) {
        reject(error);
        return;
      }

      resolve(Object.fromEntries(
        (attributes || []).map((attribute) => [
          attribute.getName(),
          attribute.getValue(),
        ]),
      ));
    });
  });
}

async function updateCognitoNameAttributes(context) {
  const { user } = context;
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
    const context = await getAuthenticatedCognitoContext();
    const claims = claimsFromSession(context.session);

    // ID-token claims are available immediately after login and provide a
    // reliable identity source even when an older user has no name attributes.
    emailAddressInput.value = claims.email || "";
    firstNameInput.value = claims.given_name || "";
    lastNameInput.value = claims.family_name || "";

    const response = await fetch(`${API_BASE_URL}/profile`, {
      headers: await authHeaders(),
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(getErrorMessage(data, "Could not load profile"));
    }

    profileVersion = Number(data.version ?? 0);
    preferredProviderSelect.value = data.preferredProvider || "openai";

    // DynamoDB is the compatibility fallback for existing accounts whose
    // Cognito user record predates given_name/family_name support.
    if (!firstNameInput.value) {
      firstNameInput.value = data.firstName || "";
    }
    if (!lastNameInput.value) {
      lastNameInput.value = data.lastName || "";
    }

    // Refresh from Cognito when possible, but do not make the whole Profile
    // page unusable if Cognito's attribute endpoint rejects an older session.
    try {
      const attributes = await getCognitoAttributes(context);
      emailAddressInput.value = attributes.email || emailAddressInput.value;
      firstNameInput.value = attributes.given_name || firstNameInput.value;
      lastNameInput.value = attributes.family_name || lastNameInput.value;
    } catch (attributeError) {
      console.warn("Could not refresh Cognito user attributes", attributeError);
    }
  } catch (error) {
    showProfileError(error.message || "Unable to load profile.");
  }
}

async function saveProfile() {
  clearProfileError();
  saveProfileButton.disabled = true;
  saveProfileButton.textContent = "Saving...";

  try {
    const context = await getAuthenticatedCognitoContext();

    const response = await fetch(`${API_BASE_URL}/profile`, {
      method: "PUT",
      headers: await jsonHeaders(),
      body: JSON.stringify({
        version: profileVersion,
        firstName: firstNameInput.value.trim(),
        lastName: lastNameInput.value.trim(),
        preferredProvider: preferredProviderSelect.value,
      }),
    });
    const data = await response.json();

    if (response.status === 409) {
      await loadProfile();
      throw new Error(getErrorMessage(
        data,
        "Your profile was changed elsewhere. The latest version has been loaded. Review it and try again.",
      ));
    }

    if (!response.ok) {
      throw new Error(getErrorMessage(data, "Could not save profile"));
    }

    profileVersion = Number(data.version);

    // Keep Cognito synchronized when the app client/session permits it. The
    // durable application profile remains saved even if this optional sync
    // fails for a legacy account.
    try {
      await updateCognitoNameAttributes(context);
    } catch (attributeError) {
      console.warn("Profile saved, but Cognito name sync failed", attributeError);
    }

    showProfileSavedState();
  } catch (error) {
    saveProfileButton.disabled = false;
    saveProfileButton.textContent = "Save Profile";
    showProfileError(error.message || "Unable to save profile.");
  }
}

saveProfileButton.addEventListener("click", saveProfile);
loadProfile();
