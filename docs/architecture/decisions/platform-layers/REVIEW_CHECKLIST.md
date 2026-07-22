# Architecture Decision Review Checklist

- [ ] The four layers have clear ownership and one-way dependencies.
- [ ] Shared Foundation contains only singular or multi-region shared capabilities.
- [ ] Regional sites remain symmetric and independently addressable.
- [ ] Global routing remains disabled by default.
- [ ] Production controls remain cost-gated.
- [ ] Terraform moved blocks cover every relocated deployed resource.
- [ ] Shared-foundation outputs are sufficient and do not leak unnecessary implementation details.
- [ ] A plan shows no destructive changes to Cognito or DynamoDB.
- [ ] Operational runbooks remain valid after the module-address change.
