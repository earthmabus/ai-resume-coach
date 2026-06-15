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
  * .github/workflows/test-aws.yml
* Created Terraform Deployment Workflow
  * .github/workflows/terraform.yml
    * Added Init, Validate, Plan, and Apply stages
* Created Initial Infrastructure - Lambda (ai-resume-coach-dev-api)
  * Lambda Execution Role - attached AWSLambdaBasicExecutionRole
* Created Initial Infrastructure - API Gateway 
** GET /health
** GET /version
** POST /analyze-resume

Phase 1 - Basic Infrastructure
* Save state for terraform IaC
  * ```aws s3api create-bucket --bucket earthmabus-ai-resume-coach-tfstate-940827434048 --region us-east-1
  aws s3api put-bucket-versioning --bucket earthmabus-ai-resume-coach-tfstate-940827434048 --versioning-configuration Status=Enabled
  aws s3api put-bucket-encryption --bucket earthmabus-ai-resume-coach-tfstate-940827434048 --server-side-encryption-configuration '{"Rules": [ { "ApplyServerSideEncryptionByDefault": { "SSEAlgorithm": "AES256" } } ] }'
  aws dynamodb create-table --table-name ai-resume-coach-terraform-locks --attribute-definitions AttributeName=LockID,AttributeType=S --key-schema AttributeName=LockID,KeyType=HASH --billing-mode PAY_PER_REQUEST --region us-east-1```
* Created a frontend
  * Added an S3 bucket for the static frontend code
  * TODO remove the hardcoding of backend endpoint in app.js to "https://7fyb8rvs84.execute-api.us-east-1.amazonaws.com"
  * Accessible via http://ai-resume-coach-dev-frontend-940827434048.s3-website-us-east-1.amazonaws.com

Phase 2 - Accept and Persist Resume (as text or document)
* Added the ability to persist resume text into a DynamoDB (ResumeAnalysis table) to store resume updates for future analysis
  * Note: Fields (documentBucket, documenKey, fileName) are associated with allowing pdfs to be uploaded
  * The "resumeText" field contains the text for the resume (either put in as text OR extracted from PDF and then put in)

Phase 3 - Allow evaluation by OpenAI
* Added an abstraction to support AI providers
  * Added an implementation using OpenAI
  * Note: I had to setup an API KEY at https://platform.openai.com?utm_source=chatgpt.com
  * Note: I added $5 with no automatic recharge
  * Note: I added a secret in github (Settings --> Secrets and variables --> Actions --> New repository secret --> OPENAI_API_KEY and put in the API key I was provided)
* Made calls to analyze the resume async because the amount of time to parse a PDF and analyze it with OpenAI takes more than the timeout period for the API Gateway

Phase 4 - Compare against job posting

