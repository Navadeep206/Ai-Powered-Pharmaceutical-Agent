"""Domain and Business Logic Exceptions for RootIQ."""


class RootIQBaseException(Exception):
    """Base exception for all RootIQ domain errors."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


# --- Document Processing Exceptions ---


class DocumentProcessingError(RootIQBaseException):
    """Base class for document processing errors."""

    pass


class InvalidPDFFormatError(DocumentProcessingError):
    """Raised when uploaded file is not a valid PDF or lacks %PDF- header."""

    pass


class EmptyDocumentError(DocumentProcessingError):
    """Raised when uploaded file or document contains zero bytes or zero pages."""

    pass


class OversizedDocumentError(DocumentProcessingError):
    """Raised when document exceeds byte size or page count limits."""

    pass


class CorruptedPDFError(DocumentProcessingError):
    """Raised when PDF structure is unparseable or corrupted."""

    pass


class PasswordProtectedPDFError(DocumentProcessingError):
    """Raised when PDF is encrypted or password protected."""

    pass


# --- Intake Exceptions ---


class IncidentIntakeError(RootIQBaseException):
    """Base class for incident intake errors."""

    pass


class InvalidIncidentTextError(IncidentIntakeError):
    """Raised when narrative text is empty or purely whitespace."""

    pass


class InvalidEmailInputError(IncidentIntakeError):
    """Raised when email subject or body lacks meaningful incident information."""

    pass


# --- Investigation Exceptions ---


class InvestigationError(RootIQBaseException):
    """Base class for quality investigation domain errors."""

    pass


class InvalidInvestigationDataError(InvestigationError):
    """Raised when investigation attributes violate pharmaceutical domain rules."""

    pass


class InvalidStatusTransitionError(InvestigationError):
    """Raised when an illegal investigation lifecycle status transition is attempted."""

    pass


# --- RCA Exceptions ---


class RCAError(RootIQBaseException):
    """Base class for Root Cause Analysis domain errors."""

    pass


class InvalidFiveWhysStructureError(RCAError):
    """Raised when 5-Whys levels are non-sequential or violate root cause constraints."""

    pass


class InvalidFishboneCategoryError(RCAError):
    """Raised when fishbone cause category is outside the 6M standard."""

    pass


class InvalidRCACauseStatusError(RCAError):
    """Raised when illegal cause status transitions or auto-confirmations are attempted."""

    pass


# --- Evidence Exceptions ---


class EvidenceError(RootIQBaseException):
    """Base class for evidence and gap analysis errors."""

    pass


class InvalidEvidenceDataError(EvidenceError):
    """Raised when evidence description, type, or source citation is invalid."""

    pass


# --- CAPA Exceptions ---


class CAPAError(RootIQBaseException):
    """Base class for CAPA errors."""

    pass


class InvalidCAPADataError(CAPAError):
    """Raised when CAPA remediation plan fails validation."""

    pass


class InvalidCAPAStatusError(CAPAError):
    """Raised when new CAPA action is improperly marked Approved or Completed directly."""

    pass


class InvalidCAPAStatusTransitionError(CAPAError):
    """Raised when illegal CAPA lifecycle state progression is attempted."""

    pass

