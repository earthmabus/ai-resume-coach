Frontend hosting correction overlay

Overlay from the repository root:
  unzip -o frontend-hosting-restoration-fix-overlay.zip -d .

This ZIP has repository-root paths. It replaces:
  infra/frontend.tf
  infra/variables.tf
  .github/workflows/terraform.yml

Corrections:
- Uses the existing Route 53 hosted zone resume.michaelpopovich.com.
- Uses a statically-addressed ACM DNS validation record so Terraform can plan in one pass.
- Installs the workflow steps that generate config.js, sync the frontend, and invalidate CloudFront.
