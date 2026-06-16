const confirmResult = document.getElementById("confirmResult");

const params = new URLSearchParams(window.location.search);
const emailFromUrl = params.get("email");

if (emailFromUrl) {
  document.getElementById("confirmEmail").value = emailFromUrl;
}

document.getElementById("confirmButton").addEventListener("click", () => {
  const email = document.getElementById("confirmEmail").value.trim();
  const code = document.getElementById("confirmCode").value.trim();

  if (!email || !code) {
    confirmResult.textContent = "Email and confirmation code are required.";
    return;
  }

  const user = new AmazonCognitoIdentity.CognitoUser({
    Username: email,
    Pool: userPool
  });

  confirmResult.textContent = "Confirming account...";

  user.confirmRegistration(code, true, (error) => {
    if (error) {
      confirmResult.textContent = `Confirmation failed: ${error.message || error}`;
      return;
    }

    confirmResult.textContent = "Account confirmed. Redirecting to sign in...";
    setTimeout(() => {
      window.location.href = "./login.html";
    }, 1000);
  });
});
