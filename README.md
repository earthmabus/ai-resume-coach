# MR-006A Internal Provenance Correction

This correction narrows MR-006 to internal regional and deployment
provenance.

It restores:

- Existing API response bodies
- Existing outbox worker payloads
- Existing frontend files

It keeps:

- RequestContext deployment identity
- DynamoDB deployment provenance
- Worker processing provenance
- Outbox-record provenance
- Structured regional logs
