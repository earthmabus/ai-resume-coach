const authResult = document.getElementById("authResult");

document.getElementById("loginButton").addEventListener("click", () => {
  const email = document.getElementById("loginEmail").value.trim();
  const password = document.getElementById("loginPassword").value;

  if (!email || !password) {
    authResult.textContent = "Email and password are required.";
    return;
  }

  const user = new AmazonCognitoIdentity.CognitoUser({
    Username: email,
    Pool: userPool
  });

  const authDetails = new AmazonCognitoIdentity.AuthenticationDetails({
    Username: email,
    Password: password
  });

  authResult.textContent = "Signing in...";

  user.authenticateUser(authDetails, {
    onSuccess: () => {
      window.location.href = "./resume-analysis.html";
    },
    onFailure: (error) => {
      authResult.textContent = `Login failed: ${error.message || error}`;
    }
  });
});
