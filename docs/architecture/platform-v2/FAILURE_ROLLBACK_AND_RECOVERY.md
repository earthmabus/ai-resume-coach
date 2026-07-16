# Failure, Rollback, and Recovery

- If fresh deployment fails before edge completion, correct and reapply.
- If east succeeds and west fails, keep east and repair west.
- If Cognito fails, neither authenticated site is usable; recreate identity and re-register the test user if needed.
- If CloudFront or DNS fails, validate APIs directly through outputs.
- If destroy fails because buckets contain objects or versions, preserve required data, empty managed development buckets, and rerun destroy.
- Platform V1 recovery is possible from the saved Git revision, exported state, DynamoDB backup, and document backup.
- After MR-008, rollback procedures must be revised for replicated data and consistency concerns.
