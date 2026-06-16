const authConfig = window.APP_CONFIG;

const userPool = new AmazonCognitoIdentity.CognitoUserPool({
  UserPoolId: authConfig.cognitoUserPoolId,
  ClientId: authConfig.cognitoUserPoolClientId
});

function getCurrentUser() {
  return userPool.getCurrentUser();
}

function getCurrentSession() {
  return new Promise((resolve, reject) => {
    const user = getCurrentUser();

    if (!user) {
      reject(new Error("No current user"));
      return;
    }

    user.getSession((error, session) => {
      if (error || !session || !session.isValid()) {
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

function requireAuth() {
  const user = getCurrentUser();

  if (!user) {
    window.location.href = "./login.html";
  }
}

function signOut() {
  const user = getCurrentUser();

  if (user) {
    user.signOut();
  }

  window.location.href = "./login.html";
}
