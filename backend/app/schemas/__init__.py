"""Pydantic Request and Response Schemas.

Enforces strict type validation and serialization for API boundaries:
- AuthSchemas: User login, token payloads, and 21 CFR Part 11 signing credentials.
- InvestigationSchemas: Creation, status updates, and summary schemas.
- EvidenceSchemas: Metadata, file upload payloads, and parsed telemetry.
- RCASchemas: Graph nodes, edges, Ishikawa categories, and 5-Whys structures.
- CAPASchemas: Action item specifications, target dates, and effectiveness review payloads.
- AuditSchemas: Audit query filters and cryptographically verifiable log formats.
"""

