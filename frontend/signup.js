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

    signupResult.textContent = "Signup successful. Check your email, then confirm your account.";
    setTimeout(() => {
      window.location.href = `./confirm-account.html?email=${encodeURIComponent(email)}`;
    }, 1000);
  });
});
