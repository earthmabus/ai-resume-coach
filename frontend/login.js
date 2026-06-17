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

async function signIn() {
  clearAuthError();

  const emailInput = document.getElementById("loginEmail");
  const passwordInput = document.getElementById("loginPassword");

  const email = emailInput.value.trim();
  const password = passwordInput.value;

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
