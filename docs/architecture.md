# Architecture Overview

## High-Level Architecture

User Browser
↓
S3 Static Website
↓
API Gateway
↓
Lambda API
↓
DynamoDB

For long-running AI workloads:

Lambda API
↓
SQS
↓
Worker Lambda
↓
OpenAI API
↓
DynamoDB

## Components

### Frontend

Hosted in Amazon S3.

Responsibilities:

* Resume analysis workflow
* Job matching workflow
* Resume history
* Job match history
* Result visualization

### API Lambda

Responsibilities:

* Request validation
* DynamoDB persistence
* Resume upload handling
* Queueing asynchronous jobs
* API responses

### Worker Lambda

Responsibilities:

* Resume analysis
* Job matching
* Resume tailoring
* OpenAI integration
* Updating DynamoDB records

### DynamoDB

Stores:

* Resume analyses
* Job matches
* Resume tailoring results

Single-table design using record types:

* resumeAnalysis
* jobMatch
* resumeTailoring

### SQS

Provides:

* Decoupling
* Retry handling
* Long-running workload support
* API Gateway timeout avoidance

### OpenAI

Provides:

* Resume analysis
* Job matching
* Resume tailoring

Provider abstraction allows future providers such as:

* Anthropic
* Azure OpenAI
* Bedrock

## Design Decisions

### Why Serverless?

* Minimal operational overhead
* Cost efficiency
* Fast deployment
* Easy scalability

### Why SQS?

Initial synchronous implementation exceeded API Gateway limits.

SQS allowed:

* Asynchronous processing
* Improved reliability
* Better user experience

### Why Provider Abstraction?

Allows AI providers to be replaced without changing business logic.

