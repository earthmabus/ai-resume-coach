const authConfig = window.APP_CONFIG;

const userPool = new AmazonCognitoIdentity.CognitoUserPool({
  UserPoolId: authConfig.cognitoUserPoolId,
  ClientId: authConfig.cognitoUserPoolClientId
});

function getCurrentUser() {
  return userPool.getCurrentUser();
}

function requireAuth() {
  const user = getCurrentUser();

  if (!user) {
    window.location.href = "./login.html";
    return false;
  }

  return true;
}

function getCurrentSession() {
  return new Promise((resolve, reject) => {
    const user = getCurrentUser();

    if (!user) {
      window.location.href = "./login.html";
      reject(new Error("No current user"));
      return;
    }

    user.getSession((error, session) => {
      if (error || !session || !session.isValid()) {
        window.location.href = "./login.html";
        reject(error || new Error("Invalid session"));
        return;
      }

      resolve(session);
    });
  });
}

async function authHeaders() {
  const session = await getCurrentSession();

  return {
    Authorization: `Bearer ${session.getIdToken().getJwtToken()}`
  };
}

async function jsonHeaders() {
  return {
    "Content-Type": "application/json",
    ...(await authHeaders())
  };
}

function signOut() {
  const user = getCurrentUser();

  if (user) {
    user.signOut();
  }

  window.location.href = "./login.html";
}
