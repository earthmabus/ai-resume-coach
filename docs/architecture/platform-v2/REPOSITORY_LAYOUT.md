# Target Repository Layout

```text
infra/
├── versions.tf
├── providers.tf
├── variables.tf
├── locals.tf
├── packages.tf
├── identity.tf
├── registration_notification.tf
├── regional_sites.tf
├── edge.tf
├── outputs.tf
├── terraform.tfvars.example
├── modules/
│   ├── regional_application/
│   │   ├── versions.tf
│   │   ├── variables.tf
│   │   ├── locals.tf
│   │   ├── api_gateway.tf
│   │   ├── compute.tf
│   │   ├── data.tf
│   │   ├── messaging.tf
│   │   ├── iam.tf
│   │   ├── monitoring.tf
│   │   └── outputs.tf
│   └── global_edge/
│       ├── versions.tf
│       ├── variables.tf
│       ├── locals.tf
│       ├── storage.tf
│       ├── cloudfront.tf
│       ├── route53.tf
│       ├── frontend.tf
│       └── outputs.tf
└── tests/
    ├── regional_module.tftest.hcl
    └── root_composition.tftest.hcl
```

Root files compose. Modules implement. Generated artifacts remain outside Terraform source directories.
