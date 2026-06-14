terraform {
  backend "s3" {
    bucket         = "earthmabus-ai-resume-coach-tfstate-940827434048"
    key            = "ai-resume-coach/dev/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "ai-resume-coach-terraform-locks"
    encrypt        = true
  }

  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }

  null = {
    source  = "hashicorp/null"
    version = "~> 3.2"
  }
}
