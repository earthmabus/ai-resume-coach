# AI Resume & Interview Coach 

A multi-tenant SaaS platform that helps professionals:

* Analyze resumes
* Match resumes against job descriptions
* Generate tailored resumes
* Generate interview preparation content
* Define a target career profile and receive role-specific AI feedback

## Features

### Resume Analysis

Users can:

* Input Target Career

* Input Resume (via text input or upload a PDF)
* Receive an AI powered resume assessment containing
  * Resume score
  * Resume analysis
  * Comparison against Target Career
* Manage multiple versions of Resumes

* Receive an AI powered comparison of a Resume against a Job Posting containing
  * Matched keywords (relevant for ATS system scoring)
  * Missing keywords (relevant for ATS system scoring)
  * Gap analysis highlighting missing experiences
  * Recommended resume changes to improve ATS scoring
  * Potential Interview specific questions
* Manage multiple Resume to Job Posting comparisons

* Input user profile

### Job Matching

Users can:

* Select a previously analyzed resume
* Enter a job name, description and URL
* Compare resume against job requirements
* Receive resume feedback 
* Receive interview prep questions

### Resume Tailoring

Resume tailoring provides:

* Tailored executive summary
* Improved resume bullets
* Keywords to add
* ATS optimization recommendations
* Positioning advice

## Technology Stack

Frontend

* HTML
* CSS
* JavaScript
* AWS CloudFront

* Note: Frontend stores JWT and attaches it to requests

Backend

* AWS Lambda (Python)
  * API Lambda - handles authentication, CRUD, validation, persistence, queue submission
  * Worker Lambda - handles submission of long running AI processing
* API Gateway HTTP API 
* DynamoDB
  * single table, fast access patterns (no joins), cheap at scale
  * contains primary key, sort key, and gsi1 (used for entity lookup by ID allowing retrieval without knowing primary key and secondary key)
  * Ex: 
    * user5 --> resumeX
    * user5 --> matchZ
    * matchZ --> tailoringH
    * matchZ --> interviewQ
* Amazon S3
* Amazon SQS
  * decouples user interactions from AI processing and prevents API Gateway timeouts
  * user submits resume --> API Lambda --> SQS --> Worker Lambda --> AI --> DynamoDB updates
* Amazon Cognito

* Note: API validates JWT through API Gateway authorizers

Infrastructure

* Terraform
* GitHub Actions
* OpenID Connect (OIDC)

AI Providers - supports multiple providers without changing business logic

* OpenAI GPT-5.5 (https://platform.openai.com/home)
* Rule-Based Fallback Provider

## Architecture Highlights

* Fully serverless architecture
* Infrastructure as Code
* Asynchronous AI processing
* Provider abstraction layer
* PDF and text resume support
* Cost-conscious AWS design
* Multi-user support
* User profiles
* Cognito authentication
* Interview preparation workflows

## Future Enhancements

* Notifications
* Secrets Manager integration
* CloudFront distribution
* Active/Active Disaster Recovery
  * Route 53 failover
  * Multi-region
  * Global DynamoDB Tables
  * S3 CRR
  * Cross-region SQS ?
* GDPR

