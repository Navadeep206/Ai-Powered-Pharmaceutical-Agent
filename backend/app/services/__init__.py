"""Business Logic & Service Layer.

Orchestrates core domain workflows decoupled from transport and storage layers:
- InvestigationService: Workflow transitions, state progression, and approval gates.
- EvidenceService: Evidence ingestion, parsing, and correlation indexing.
- RCAService: Coordination between user inputs, causal graphs, and AI agents.
- CAPAService: CAPA tracking, escalation triggers, and periodic review scheduling.
- AuditService: Centralized GxP audit logging adhering to ALCOA+ data integrity rules.
"""

