const authResult = document.getElementById("authResult");

document.getElementById("loginButton").addEventListener("click", () => {
  const email = document.getElementById("loginEmail").value.trim();
  const password = document.getElementById("loginPassword").value;

  const user = new AmazonCognitoIdentity.CognitoUser({
    Username: email,
    Pool: userPool
  });

  const authDetails = new AmazonCognitoIdentity.AuthenticationDetails({
    Username: email,
    Password: password
  });

  user.authenticateUser(authDetails, {
    onSuccess: () => {
      window.location.href = "./resume-analysis.html";
    },
    onFailure: (error) => {
      authResult.textContent = `Login failed: ${error.message || error}`;
    }
  });
});

document.getElementById("signupButton").addEventListener("click", () => {
  const email = document.getElementById("signupEmail").value.trim();
  const password = document.getElementById("signupPassword").value;

  userPool.signUp(email, password, [], null, (error) => {
    if (error) {
      authResult.textContent = `Signup failed: ${error.message || error}`;
      return;
    }

    authResult.textContent = "Signup successful. Check your email for a confirmation code.";
  });
});

document.getElementById("confirmButton").addEventListener("click", () => {
  const email = document.getElementById("confirmEmail").value.trim();
  const code = document.getElementById("confirmCode").value.trim();

  const user = new AmazonCognitoIdentity.CognitoUser({
    Username: email,
    Pool: userPool
  });

  user.confirmRegistration(code, true, (error) => {
    if (error) {
      authResult.textContent = `Confirmation failed: ${error.message || error}`;
      return;
    }

    authResult.textContent = "Account confirmed. You can now sign in.";
  });
});
