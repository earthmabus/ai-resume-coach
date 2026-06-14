Created execution environment
* Fedora Linux VM
* AWS CLI
* Terraform
* Git
* GitHub
* Python

Created Management Account with the following responsibilities
* AWS Organizations
* Billing
* Budgets
* Cost Anomaly Detection
* Account Governance

Created Portfolio Account 
* Account Name: mpopsaws+portfolio-ai-resume-coach
* Account ID: 940827434048
* Configured budgets $10/mo
* Configured billing alerts
* TODO enable Cost Anomaly Detection

Created GitHub Repo
* github.com/earthmabus/ai-resume-coach
* Enabled OIDC Authentication
* Created Deploy Role (GitHubActionsDeployRole)
* Created Terraform Role (GitHubActionsTerraformRole-ai-resume-coach)
* Created Test AWS Access Workflow
** .github/workflows/test-aws.yml
* Created Terraform Deployment Workflow
** .github/workflows/terraform.yml
*** Added Init, Validate, Plan, and Apply stages
* Created Initial Infrastructure - Lambda (ai-resume-coach-dev-api)
** Lambda Execution Role - attached AWSLambdaBasicExecutionRole
* Created Initial Infrastructure - API Gateway 
** GET /health
** GET /version
** POST /analyze-resume
