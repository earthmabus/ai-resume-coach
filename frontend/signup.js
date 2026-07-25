const signupResult = document.getElementById("signupResult");

document.getElementById("signupButton").addEventListener("click", () => {
  const firstName = document.getElementById("signupFirstName").value.trim();
  const lastName = document.getElementById("signupLastName").value.trim();
  const email = document.getElementById("signupEmail").value.trim();
  const password = document.getElementById("signupPassword").value;
  const confirmPassword = document.getElementById("signupPasswordConfirm").value;

  if (!firstName || !lastName || !email || !password || !confirmPassword) {
    signupResult.textContent = (
      "First name, last name, email, password, and password confirmation are required."
    );
    return;
  }

  if (password !== confirmPassword) {
    signupResult.textContent = "Passwords do not match.";
    return;
  }

  signupResult.textContent = "Creating account...";

  const attributes = [
    new AmazonCognitoIdentity.CognitoUserAttribute({
      Name: "given_name",
      Value: firstName,
    }),
    new AmazonCognitoIdentity.CognitoUserAttribute({
      Name: "family_name",
      Value: lastName,
    }),
  ];

  userPool.signUp(email, password, attributes, null, (error) => {
    if (error) {
      signupResult.textContent = `Signup failed: ${error.message || error}`;
      return;
    }

    signupResult.textContent = (
      "Account created. Check your email and click the verification link, "
      + "then return here to sign in."
    );
    setTimeout(() => {
      window.location.href = "./login.html?signup=success";
    }, 2000);
  });
});
