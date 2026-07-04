const signupResult = document.getElementById("signupResult");

document.getElementById("signupButton").addEventListener("click", () => {
  const email = document.getElementById("signupEmail").value.trim();
  const password = document.getElementById("signupPassword").value;
  const confirmPassword = document.getElementById("signupPasswordConfirm").value;

  if (!email || !password || !confirmPassword) {
    signupResult.textContent = "Email, password, and password confirmation are required.";
    return;
  }

  if (password !== confirmPassword) {
    signupResult.textContent = "Passwords do not match.";
    return;
  }

  signupResult.textContent = "Creating account...";

  userPool.signUp(email, password, [], null, (error) => {
    if (error) {
      signupResult.textContent = `Signup failed: ${error.message || error}`;
      return;
    }

    signupResult.textContent =
      "Account created. Check your email and click the verification link, then return here to sign in.";
    setTimeout(() => {
      window.location.href = "./login.html?signup=success";
    }, 2000);
  });
});
