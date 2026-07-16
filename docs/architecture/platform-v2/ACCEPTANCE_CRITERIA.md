# Platform V2 / MR-007 Acceptance Criteria

## Architecture
- [ ] East and west use the same regional module.
- [ ] Root contains no regional compute implementation.
- [ ] Global resources are created once.
- [ ] Provider aliases are explicit.
- [ ] Naming is symmetric and region-qualified.

## Build and test
- [ ] Python tests pass.
- [ ] Package tests pass.
- [ ] Terraform fmt, validate, and test pass.
- [ ] Fresh-state plan is reviewed.

## Regional isolation
- [ ] Each API uses its own table, bucket, and queue.
- [ ] Each publisher sends only locally.
- [ ] Each worker consumes only locally.
- [ ] No runtime requires cross-region access in MR-007.

## Shared services
- [ ] One Cognito pool serves both APIs.
- [ ] One registration-notification path exists.
- [ ] One frontend and CloudFront distribution exist.
- [ ] Frontend intentionally points to east.

## Runtime validation
- [ ] East health reports `us-east-1`.
- [ ] West health reports `us-west-2`.
- [ ] Both versions report the same deployment ID.
- [ ] Both publisher and worker smoke tests pass.
- [ ] Authentication works against both APIs.
- [ ] End-to-end resume processing works in both Regions.

## Operations
- [ ] Regional dashboards and alarms exist.
- [ ] DLQs are empty after testing.
- [ ] Terraform returns no changes.

## Documentation
- [ ] Design committed.
- [ ] Rebuild outcomes and pivots recorded.
- [ ] Poster regeneration remains scheduled for final active-active completion.
