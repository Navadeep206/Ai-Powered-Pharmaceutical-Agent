import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useSelector, useDispatch } from 'react-redux';
import {
  setIntakeMethod,
  setIntakeFile,
  clearIntakeFile,
  setIntakeText,
  setIntakeEmail,
  setExtractionState,
  setExtractedData,
  updateExtractedField,
  resetDraftIntake,
  createNewInvestigationFromIntake,
} from '../../redux/slices/investigationSlice';
import PageHeader from '../../components/common/PageHeader';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../../components/common/Card';
import Button from '../../components/common/Button';
import StatusBadge from '../../components/common/StatusBadge';
import IntakeMethodSelector from '../../components/investigation/IntakeMethodSelector';
import DocumentUpload from '../../components/investigation/DocumentUpload';
import IncidentDescriptionInput from '../../components/investigation/IncidentDescriptionInput';
import EmailIncidentInput from '../../components/investigation/EmailIncidentInput';
import ExtractionReviewForm from '../../components/investigation/ExtractionReviewForm';
import { SAMPLE_EXTRACTED_PAYLOAD } from '../../utils/demoData';
import {
  ArrowLeft,
  Sparkles,
  RotateCcw,
  AlertCircle,
  Loader2,
  FileSearch,
} from 'lucide-react';

/**
 * Start New Investigation Page supporting multi-modal intake and AI extraction review.
 */
export default function NewInvestigationPage() {
  const navigate = useNavigate();
  const dispatch = useDispatch();

  const { draftIntake } = useSelector((state) => state.investigations);
  const {
    method,
    fileInfo,
    rawText,
    emailSubject,
    emailBody,
    extractionState,
    extractedData,
  } = draftIntake;

  const [validationError, setValidationError] = useState(null);
  const [draftSavedToast, setDraftSavedToast] = useState(false);

  // Validate the active intake method before transitioning to simulated extraction
  const handleAnalyzeIncident = () => {
    setValidationError(null);

    if (method === 'upload') {
      if (!fileInfo) {
        setValidationError('Please select or drag a valid PDF document to proceed.');
        return;
      }
    } else if (method === 'text') {
      if (!rawText || rawText.trim().length < 20) {
        setValidationError('Please provide a descriptive incident narrative (at least 20 characters).');
        return;
      }
    } else if (method === 'email') {
      if (!emailSubject?.trim() && !emailBody?.trim()) {
        setValidationError('Please provide an email subject header or body content to analyze.');
        return;
      }
    }

    // Begin simulated AI extraction
    dispatch(setExtractionState('analyzing'));

    // Simulated short analysis delay (1.2s)
    setTimeout(() => {
      // Seed extraction payload with any contextual values from the input
      const payload = JSON.parse(JSON.stringify(SAMPLE_EXTRACTED_PAYLOAD));

      if (method === 'text' && rawText) {
        payload.incidentInfo.incidentDescription = rawText;
      } else if (method === 'email') {
        if (emailSubject) payload.incidentInfo.incidentTitle = emailSubject;
        if (emailBody) payload.incidentInfo.incidentDescription = emailBody;
      } else if (method === 'upload' && fileInfo) {
        payload.context.initialObservations = `Extracted from PDF upload: ${fileInfo.name} (${fileInfo.size}). Batch records corroboration pending.`;
      }

      dispatch(setExtractedData(payload));
    }, 1200);
  };

  const handleUpdateExtractedField = (section, field, value) => {
    dispatch(updateExtractedField({ section, field, value }));
  };

  const handleSaveDraft = () => {
    setDraftSavedToast(true);
    setTimeout(() => setDraftSavedToast(false), 3000);
  };

  const handleContinueToRCA = () => {
    if (!extractedData) return;
    // Dispatch creation of new investigation record in local state and navigate to workspace
    const newId = dispatch(createNewInvestigationFromIntake({ extractedData })).payload;
    navigate(`/investigations/${newId || 'INV-2026-001'}`);
  };

  const handleResetIntake = () => {
    dispatch(resetDraftIntake());
    setValidationError(null);
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Page Header */}
      <PageHeader
        title="Start New Investigation"
        description="Submit incident information to initiate an AI-assisted quality investigation."
        breadcrumbs={[
          { label: 'RootIQ', to: '/' },
          { label: 'Investigations', to: '/investigations' },
          { label: 'New Intake' },
        ]}
        badge={
          extractionState === 'extracted' ? (
            <StatusBadge variant="teal">Extraction Review</StatusBadge>
          ) : (
            <StatusBadge variant="neutral">Intake Stage</StatusBadge>
          )
        }
        actions={
          <div className="flex items-center space-x-2">
            <Link to="/investigations">
              <Button variant="secondary" size="sm" leftIcon={ArrowLeft}>
                Back to Registry
              </Button>
            </Link>
            {extractionState === 'extracted' && (
              <Button
                variant="ghost"
                size="sm"
                leftIcon={RotateCcw}
                onClick={handleResetIntake}
              >
                Change Intake Source
              </Button>
            )}
          </div>
        }
      />

      {/* State A: Intake Input Selection State */}
      {extractionState === 'idle' && (
        <div className="space-y-6">
          {/* Method Selector */}
          <div>
            <h3 className="text-xs font-semibold text-[#142B45] uppercase tracking-wider mb-2">
              Select Intake Method
            </h3>
            <IntakeMethodSelector
              selectedMethod={method}
              onSelectMethod={(m) => {
                dispatch(setIntakeMethod(m));
                setValidationError(null);
              }}
            />
          </div>

          {/* Active Intake Form Container */}
          <Card>
            <CardHeader>
              <div>
                <CardTitle>
                  {method === 'upload' && 'Upload Incident Documentation'}
                  {method === 'text' && 'Paste Unstructured Incident Narrative'}
                  {method === 'email' && 'Email Alert or Correspondence Intake'}
                </CardTitle>
                <CardDescription>
                  {method === 'upload' &&
                    'Select a Batch Manufacturing Record (BMR) or SCADA excursion PDF.'}
                  {method === 'text' &&
                    'Paste raw operator logs or initial QA notification statements.'}
                  {method === 'email' &&
                    'Enter subject line and body of deviation notification email.'}
                </CardDescription>
              </div>
              <StatusBadge variant="neutral" size="sm">
                Local Input
              </StatusBadge>
            </CardHeader>

            <CardContent>
              {method === 'upload' && (
                <DocumentUpload
                  fileInfo={fileInfo}
                  onFileSelect={(f) => dispatch(setIntakeFile(f))}
                  onFileRemove={() => dispatch(clearIntakeFile())}
                  error={validationError}
                  setError={setValidationError}
                />
              )}

              {method === 'text' && (
                <IncidentDescriptionInput
                  value={rawText}
                  onChange={(txt) => {
                    dispatch(setIntakeText(txt));
                    if (validationError) setValidationError(null);
                  }}
                  error={validationError}
                />
              )}

              {method === 'email' && (
                <EmailIncidentInput
                  subject={emailSubject}
                  body={emailBody}
                  onSubjectChange={(subj) => {
                    dispatch(setIntakeEmail({ subject: subj, body: emailBody }));
                    if (validationError) setValidationError(null);
                  }}
                  onBodyChange={(bdy) => {
                    dispatch(setIntakeEmail({ subject: emailSubject, body: bdy }));
                    if (validationError) setValidationError(null);
                  }}
                  error={validationError}
                />
              )}
            </CardContent>

            <CardFooter className="py-4 bg-[#F8FAFC]">
              <div className="text-xs text-[#64748B]">
                Extraction maps entities into standard 21 CFR Part 11 investigation schema.
              </div>

              <Button
                variant="accent"
                size="md"
                leftIcon={Sparkles}
                onClick={handleAnalyzeIncident}
              >
                Analyze Incident
              </Button>
            </CardFooter>
          </Card>
        </div>
      )}

      {/* State B: Simulated AI Analyzing Progress State */}
      {extractionState === 'analyzing' && (
        <Card className="py-16 text-center shadow-md">
          <CardContent className="space-y-4 max-w-md mx-auto">
            <div className="w-14 h-14 rounded-full bg-[#E6F7F5] text-[#0F9D91] flex items-center justify-center mx-auto animate-pulse">
              <FileSearch className="w-7 h-7 text-[#0F9D91]" />
            </div>

            <div className="space-y-1">
              <h3 className="text-lg font-bold text-[#142B45]">
                Analyzing Incident Intake
              </h3>
              <p className="text-xs text-[#64748B]">
                Simulating entity extraction: extracting batch IDs, process parameters, excursion timestamps, and initial observations...
              </p>
            </div>

            <div className="pt-4 flex items-center justify-center space-x-2 text-xs font-semibold text-[#0F9D91]">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Generating demonstration extraction review...</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* State C: Structured Extraction Review Experience */}
      {extractionState === 'extracted' && extractedData && (
        <ExtractionReviewForm
          extractedData={extractedData}
          onUpdateField={handleUpdateExtractedField}
          onSaveDraft={handleSaveDraft}
          onContinueToRCA={handleContinueToRCA}
          isDraftSaved={draftSavedToast}
        />
      )}
    </div>
  );
}
