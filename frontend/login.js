const loginButton = document.getElementById("loginButton");
const authError = document.getElementById("authError");
const resendVerificationButton = document.getElementById("resendVerificationButton");
const resendVerificationPanel = document.getElementById("resendVerificationPanel");
const resendVerificationSubmit = document.getElementById("resendVerificationSubmit");
const resendVerificationResult = document.getElementById("resendVerificationResult");
const resendEmail = document.getElementById("resendEmail");
const loginEmail = document.getElementById("loginEmail");

const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

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

  const email = loginEmail.value.trim();
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

function resendVerificationEmail(email) {
  return new Promise((resolve, reject) => {
    const cognitoUser = new AmazonCognitoIdentity.CognitoUser({
      Username: email,
      Pool: userPool,
    });

    cognitoUser.resendConfirmationCode((error, result) => {
      if (error) {
        reject(error);
        return;
      }

      resolve(result);
    });
  });
}

function setResendButtonState(text, disabled) {
  resendVerificationSubmit.textContent = text;
  resendVerificationSubmit.disabled = disabled;
}

function updateResendButtonState() {
  const email = resendEmail.value.trim();
  resendVerificationSubmit.disabled = !emailRegex.test(email);
}

resendEmail.addEventListener("input", updateResendButtonState);

loginButton.addEventListener("click", signIn);

document.getElementById("loginPassword").addEventListener("keydown", event => {
  if (event.key === "Enter") {
    signIn();
  }
});

if (resendVerificationButton) {
  resendVerificationButton.addEventListener("click", () => {
    if (resendVerificationPanel.classList.contains("hidden")) {
      resendVerificationPanel.classList.remove("hidden");

      resendEmail.value = loginEmail.value.trim();

      updateResendButtonState();
      resendEmail.focus();
      resendEmail.select();
    }
  });
}

if (resendVerificationSubmit) {
  resendVerificationSubmit.addEventListener("click", async () => {
    const email = resendEmail.value.trim();

    if (!emailRegex.test(email)) {
      resendVerificationResult.textContent = "Please enter a valid email address.";
      return;
    }

    setResendButtonState("Sending...", true);
    resendVerificationResult.textContent = "";

    try {
      await resendVerificationEmail(email);
      setResendButtonState("Sent ✓", true);
      resendVerificationResult.textContent = `Verification email sent to ${email}. Check your inbox and spam folder.`;
      setTimeout(() => {
        resendVerificationResult.textContent = "";
        setResendButtonState("Send Verification Email", false);
        loginEmail.value = resendEmail.value;
        resendEmail.value = "";
        resendVerificationPanel.classList.add("hidden");
        updateResendButtonState();
        loginEmail.focus();
      }, 5000);

    } catch (error) {
      switch (error.code) {
        case "UserNotFoundException":
          resendVerificationResult.textContent = "No account exists with that email address.";
          break;

        case "InvalidParameterException":
          resendVerificationResult.textContent = "This account has already been verified.";
          break;

        case "LimitExceededException":
          resendVerificationResult.textContent = "Too many requests. Please wait a few minutes and try again.";
          break;

        default:
          resendVerificationResult.textContent = `Unable to resend verification email: ${error.message || error}`;
      }
      setResendButtonState("Send Verification Email", false);

      // Re-enable the button if the email is still valid.
      updateResendButtonState();
    }
  });
}
