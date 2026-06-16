# ai-resume-coach

# AI Resume & Interview Coach for Engineering Leaders

AI Resume & Interview Coach is a serverless AWS application that helps engineering leaders improve resumes, evaluate job fit, and generate tailored resume recommendations using AI.

The application supports:

* Resume analysis (provide text or upload a PDF)
* AI-powered resume scoring
* Resume history management
* Job description matching
* Resume tailoring recommendations for specific jobs

## Features

### Resume Analysis

Users can:

* Provide resumes as text or upload as PDFs
* Analyze resumes using AI
* Review historical analyses of previous resume versions
* Download previously uploaded resumes

Each analysis provides:

* Overall score
* Leadership score
* Technical score
* Architecture score
* ATS score
* Executive summary
* Strengths
* Recommendations
* Gap analysis

### Job Matching

Users can:

* Select a previously analyzed resume
* Enter a job name
* Enter a job URL
* Paste a job description
* Compare resume against job requirements

Job matching provides:

* Match score
* Missing keywords
* Strengths
* Weaknesses
* Executive assessment

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

Backend

* AWS Lambda (Python)
* API Gateway HTTP API
* DynamoDB
* Amazon S3
* Amazon SQS

Infrastructure

* Terraform
* GitHub Actions
* OpenID Connect (OIDC)

AI Providers

* OpenAI GPT-5.5
* Rule-Based Fallback Provider

## Architecture Highlights

* Fully serverless architecture
* Infrastructure as Code
* Asynchronous AI processing
* Provider abstraction layer
* PDF and text resume support
* Cost-conscious AWS design

## Future Enhancements

* User profiles
* Notifications
* Secrets Manager integration
* CloudFront distribution
* Cognito authentication
* Multi-user support
* Interview preparation workflows

