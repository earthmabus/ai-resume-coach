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
* Account ID: 
* Configured budgets $10/mo
* Configured billing alerts
* TODO enable Cost Anomaly Detection

Setup GitHub Repo
* github.com/earthmabus/ai-resume-coach
* Enabled OIDC Authentication
* Created Deploy Role (GitHubActionsDeployRole)
* Created Terraform Role (GitHubActionsTerraformRole-ai-resume-coach)
* Created Test AWS Access Workflow
  * .github/workflows/test-aws.yml
* Created Terraform Deployment Workflow
  * .github/workflows/terraform.yml
    * Added Init, Validate, Plan, and Apply stages
* Created Initial Infrastructure - Lambda (ai-resume-coach-dev-api)
  * Lambda Execution Role - attached AWSLambdaBasicExecutionRole

OpenAI
  * Setup an API KEY at https://platform.openai.com?utm_source=chatgpt.com
  * Added a secret in github (Settings --> Secrets and variables --> Actions --> New repository secret --> OPENAI_API_KEY and put in the API key I was provided)

Other
  * Accessible via http://ai-resume-coach-dev-frontend-940827434048.s3-website-us-east-1.amazonaws.com
