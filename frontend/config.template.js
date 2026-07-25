// Source template for frontend runtime configuration.
// tools/operations/deploy_frontend.sh renders environment-specific values into
// a temporary deployment directory; this repository file stays environment-neutral.
window.APP_CONFIG = {
  apiEndpoint: "",
  cognitoUserPoolId: "",
  cognitoUserPoolClientId: ""
};
