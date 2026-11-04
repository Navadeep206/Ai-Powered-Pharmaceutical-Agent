"""SQLAlchemy ORM Domain Models.

Architectural module responsible for pharmaceutical manufacturing data persistence:
- Deviation: Deviation and Out-of-Specification (OOS) event records.
- BatchRecord: API production batch numbers, parameters, and yield logs.
- Investigation: Lifecycle and stage tracking for RCA investigations.
- EvidenceArtifact: Associated chromatography reports, sensor telemetry, and operator notes.
- RCANode: Causal relationship tree, Ishikawa 6M classification, and 5-Whys depth.
- CAPAAction: Corrective and Preventive Actions with deadlines, assignees, and verification.
- AuditTrailEntry: GxP 21 CFR Part 11 compliant immutable audit log with e-signatures.
"""

