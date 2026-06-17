const loginButton = document.getElementById("loginButton");
const authError = document.getElementById("authError");

function showAuthError(message) {
  authError.textContent = message;
  authError.classList.remove("hidden");
}

function clearAuthError() {
  authError.textContent = "";
  authError.classList.add("hidden");
}

function signInUser(email, password) {
  return new Promise((resolve, reject) => {
    const authenticationDetails =
      new AmazonCognitoIdentity.AuthenticationDetails({
        Username: email,
        Password: password
      });

    const cognitoUser = new AmazonCognitoIdentity.CognitoUser({
      Username: email,
      Pool: userPool
    });

    cognitoUser.authenticateUser(authenticationDetails, {
      onSuccess: resolve,
      onFailure: reject,
      newPasswordRequired: () => {
        reject(new Error("A new password is required before signing in."));
      }
    });
  });
}

async function signIn() {
  clearAuthError();

  const email = document.getElementById("loginEmail").value.trim();
  const password = document.getElementById("loginPassword").value;

  if (!email || !password) {
    showAuthError("Email and password are required.");
    return;
  }

  loginButton.disabled = true;
  loginButton.textContent = "Signing in...";

  try {
    await signInUser(email, password);
    window.location.href = "./index.html";
  } catch (error) {
    showAuthError(error.message || "Unable to sign in. Check your email and password.");
  } finally {
    loginButton.disabled = false;
    loginButton.textContent = "Sign In";
  }
}

loginButton.addEventListener("click", signIn);

document.getElementById("loginPassword").addEventListener("keydown", event => {
  if (event.key === "Enter") {
    signIn();
  }
});
