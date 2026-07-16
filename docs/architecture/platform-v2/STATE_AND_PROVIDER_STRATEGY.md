# Terraform State and Provider Strategy

## State

Platform V2 initially uses one Terraform state for the full development environment. One operator, one release workflow, and explicit cross-layer dependencies make a state split premature.

The existing S3 backend remains authoritative. The pre-rebuild state export remains outside the repository.

## Providers

```hcl
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}

provider "aws" {
  alias  = "us_west_2"
  region = "us-west-2"
}

provider "aws" {
  alias  = "us_east_2"
  region = "us-east-2"
}
```

`us-east-2` is reserved for the later MRSC witness/data layer.

## Module wiring

```hcl
module "east" {
  source = "./modules/regional_application"
  providers = { aws = aws.us_east_1 }
}

module "west" {
  source = "./modules/regional_application"
  providers = { aws = aws.us_west_2 }
}
```

The provider alias and explicit Region input must agree.

## Future split

A later split may separate global edge/identity, multi-region data, and regional applications only when teams, release cadence, or blast-radius requirements justify it.

## Drift discipline

Local Terraform and CI must not apply concurrently. Before local work: `git pull --ff-only`, `git status --short`, and verify the deployment ID matches the code being applied.
