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
  revertExtractedField,
  resetDraftIntake,
  createInvestigationAsync,
  analyzeIncidentIntake,
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
import {
  buildInvestigationPayloadFromReviewedData,
  normalizeExtractionResponse,
} from '../../utils/normalizers';
import {
  ArrowLeft,
  ArrowRight,
  Sparkles,
  RotateCcw,
  AlertCircle,
  Loader2,
  FileSearch,
  CheckCircle2,
  UploadCloud,
  Cpu,
  ShieldCheck,
  AlertTriangle,
} from 'lucide-react';

/**
 * Start New Investigation Page supporting real multi-modal intake and AI extraction review.
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
    analysisProgress,
    extractionError,
    extractedData,
  } = draftIntake;

  // Keep raw File object in local state (prevent storing non-serializable objects in Redux)
  const [selectedFile, setSelectedFile] = useState(null);
  const [validationError, setValidationError] = useState(null);
  const [draftSavedToast, setDraftSavedToast] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Validate active intake method and dispatch real AI extraction
  const handleAnalyzeIncident = async () => {
    setValidationError(null);

    if (method === 'upload') {
      if (!selectedFile && !fileInfo) {
        setValidationError('Please select or drag a valid PDF document to proceed.');
        return;
      }
    } else if (method === 'text') {
      if (!rawText || rawText.trim().length < 15) {
        setValidationError('Please provide a descriptive incident narrative (at least 15 characters).');
        return;
      }
    } else if (method === 'email') {
      if (!emailSubject?.trim() && !emailBody?.trim()) {
        setValidationError('Please provide an email subject header or body content to analyze.');
        return;
      }
    }

    try {
      const resultAction = await dispatch(
        analyzeIncidentIntake({
          method,
          file: selectedFile,
          rawText,
          emailSubject,
          emailBody,
        })
      );

      if (analyzeIncidentIntake.rejected.match(resultAction)) {
        setValidationError(
          resultAction.payload?.message ||
            'AI extraction could not be completed. You can retry or proceed with manual form entry.'
        );
      }
    } catch (err) {
      setValidationError(err.message || 'An unexpected error occurred during incident analysis.');
    }
  };

  const handleUpdateExtractedField = (section, field, value, canonicalKey) => {
    dispatch(updateExtractedField({ section, field, value, canonicalKey }));
  };

  const handleRevertExtractedField = (section, field, canonicalKey) => {
    dispatch(revertExtractedField({ section, field, canonicalKey }));
  };

  const handleSaveDraft = () => {
    setDraftSavedToast(true);
    setTimeout(() => setDraftSavedToast(false), 3000);
  };

  const handleContinueToRCA = async () => {
    if (!extractedData) return;
    setIsSubmitting(true);
    setValidationError(null);

    const severityVal = extractedData.incidentInfo?.severity;
    const validSeverities = ['Critical', 'High', 'Medium', 'Low'];
    if (!severityVal || !validSeverities.includes(severityVal)) {
      setValidationError(
        'Deviation Severity has not been assigned. Please assess and select a severity level (Critical, High, Medium, or Low) based on investigator review before continuing to RCA.'
      );
      setIsSubmitting(false);
      return;
    }

    try {
      const payload = buildInvestigationPayloadFromReviewedData(extractedData);
      const resultAction = await dispatch(createInvestigationAsync(payload));

      if (createInvestigationAsync.fulfilled.match(resultAction)) {
        const created = resultAction.payload;
        const targetId = created.id || created.investigation_id;
        navigate(`/investigations/${encodeURIComponent(targetId)}`);
      } else {
        setValidationError(
          resultAction.payload?.message || 'Failed to persist investigation in database.'
        );
      }
    } catch (err) {
      setValidationError(err.message || 'An unexpected error occurred while saving investigation.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResetIntake = () => {
    setSelectedFile(null);
    dispatch(resetDraftIntake());
    setValidationError(null);
  };

  // Fallback to manual entry if AI extraction service encounters an error
  const handleProceedWithManualEntry = () => {
    const fallbackResponse = normalizeExtractionResponse({
      analysis_id: `MANUAL-${Date.now()}`,
      intake_method: method === 'upload' ? 'Document' : method === 'email' ? 'Email' : 'Text',
      extraction_status: 'NEEDS_REVIEW',
      completeness_score: 25.0,
      overall_confidence: 0.5,
      extracted_data: {
        incident_title: { value: emailSubject || (method === 'upload' ? fileInfo?.name : 'Quality Deviation Intake') },
        incident_description: { value: rawText || emailBody || '' },
      },
    });

    dispatch(setExtractedData(fallbackResponse));
    setValidationError(null);
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Page Header */}
      <PageHeader
        title="Start New Investigation"
        description="Submit incident information via PDF, narrative text, or email alert to initiate an AI-assisted quality investigation."
        breadcrumbs={[
          { label: 'RootIQ', to: '/' },
          { label: 'Investigations', to: '/investigations' },
          { label: 'New Intake' },
        ]}
        badge={
          extractionState === 'extracted' ? (
            <StatusBadge variant="teal">Extraction Review</StatusBadge>
          ) : extractionState === 'analyzing' ? (
            <StatusBadge variant="warning">Analyzing</StatusBadge>
          ) : extractionState === 'failed' ? (
            <StatusBadge variant="danger">Review Required</StatusBadge>
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
            {(extractionState === 'extracted' || extractionState === 'failed') && (
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

      {/* State: Intake, Analyzing, or Extraction Failed (Page always stays visible!) */}
      {extractionState !== 'extracted' && (
        <div className="space-y-6">
          {/* Active Error Banner when extraction failed */}
          {extractionState === 'failed' && (
            <Card className="border-[#FECACA] bg-[#FEF2F2]/50 shadow-xs">
              <CardHeader className="pb-3">
                <div className="flex items-center space-x-2.5 text-[#991B1B]">
                  <AlertTriangle className="w-5 h-5 text-[#DC2626] shrink-0" />
                  <CardTitle className="text-sm font-semibold text-[#991B1B]">AI Extraction Notice</CardTitle>
                </div>
                <CardDescription className="text-xs text-[#7F1D1D] mt-1">
                  {extractionError ||
                    validationError ||
                    'The extraction pipeline could not process the provided intake content automatically.'}
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-0 pb-3">
                <p className="text-xs text-[#991B1B]">
                  Your uploaded file and form inputs are preserved. You can retry the AI analysis, update the document, or proceed directly with manual entry.
                </p>
              </CardContent>
              <CardFooter className="flex items-center justify-between py-3 px-6 bg-[#FEF2F2] border-t border-[#FCA5A5]/40">
                <Button
                  variant="ghost"
                  size="sm"
                  leftIcon={RotateCcw}
                  onClick={handleResetIntake}
                >
                  Clear & Reset
                </Button>
                <div className="flex items-center space-x-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    leftIcon={Sparkles}
                    onClick={handleAnalyzeIncident}
                    disabled={extractionState === 'analyzing'}
                  >
                    Retry Analysis
                  </Button>
                  <Button
                    variant="accent"
                    size="sm"
                    rightIcon={ArrowRight}
                    onClick={handleProceedWithManualEntry}
                  >
                    Proceed with Manual Entry
                  </Button>
                </div>
              </CardFooter>
            </Card>
          )}

          {/* Real AI Analyzing Progress Card - Displayed while processing */}
          {extractionState === 'analyzing' && (
            <Card className="border-[#0F9D91]/30 bg-[#F0FDFA] shadow-xs">
              <CardContent className="py-5 px-6 space-y-4">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 rounded-xl bg-[#E6F7F5] text-[#0F9D91] flex items-center justify-center shrink-0 animate-pulse">
                    <FileSearch className="w-5 h-5 text-[#0F9D91]" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-[#142B45]">
                      Analyzing Quality Incident Intake
                    </h3>
                    <p className="text-xs text-[#64748B]">
                      Processing incident through LangGraph extraction nodes and 21 CFR Part 11 entity mapping...
                    </p>
                  </div>
                </div>

                {/* 4-Step Progress Stepper: Uploading → Extracting document → AI analysis → Results ready */}
                <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 bg-white p-3.5 rounded-xl border border-[#CCFBF1]">
                  {/* Step 1: Uploading */}
                  <div className="flex items-center space-x-2 text-xs">
                    {analysisProgress === 'uploading' ? (
                      <Loader2 className="w-4 h-4 text-[#0F9D91] animate-spin shrink-0" />
                    ) : (
                      <CheckCircle2 className="w-4 h-4 text-[#059669] shrink-0" />
                    )}
                    <span className={analysisProgress === 'uploading' ? 'font-semibold text-[#142B45]' : 'text-[#059669]'}>
                      1. Uploading
                    </span>
                  </div>

                  {/* Step 2: Extracting document */}
                  <div className="flex items-center space-x-2 text-xs">
                    {analysisProgress === 'extracting' || analysisProgress === 'ocr_required' ? (
                      <Loader2 className="w-4 h-4 text-[#0F9D91] animate-spin shrink-0" />
                    ) : analysisProgress === 'analyzing' || analysisProgress === 'results_ready' || analysisProgress === 'completed' ? (
                      <CheckCircle2 className="w-4 h-4 text-[#059669] shrink-0" />
                    ) : (
                      <div className="w-4 h-4 rounded-full border-2 border-[#CBD5E1] shrink-0" />
                    )}
                    <span className={
                      analysisProgress === 'extracting' || analysisProgress === 'ocr_required'
                        ? 'font-semibold text-[#142B45]'
                        : analysisProgress === 'analyzing' || analysisProgress === 'results_ready' || analysisProgress === 'completed'
                        ? 'text-[#059669]'
                        : 'text-[#64748B]'
                    }>
                      2. Extracting document
                    </span>
                  </div>

                  {/* Step 3: AI analysis */}
                  <div className="flex items-center space-x-2 text-xs">
                    {analysisProgress === 'analyzing' ? (
                      <Loader2 className="w-4 h-4 text-[#0F9D91] animate-spin shrink-0" />
                    ) : analysisProgress === 'results_ready' || analysisProgress === 'completed' ? (
                      <CheckCircle2 className="w-4 h-4 text-[#059669] shrink-0" />
                    ) : (
                      <div className="w-4 h-4 rounded-full border-2 border-[#CBD5E1] shrink-0" />
                    )}
                    <span className={
                      analysisProgress === 'analyzing'
                        ? 'font-semibold text-[#142B45]'
                        : analysisProgress === 'results_ready' || analysisProgress === 'completed'
                        ? 'text-[#059669]'
                        : 'text-[#64748B]'
                    }>
                      3. AI analysis
                    </span>
                  </div>

                  {/* Step 4: Results ready */}
                  <div className="flex items-center space-x-2 text-xs">
                    {analysisProgress === 'results_ready' || analysisProgress === 'completed' ? (
                      <CheckCircle2 className="w-4 h-4 text-[#059669] shrink-0" />
                    ) : (
                      <div className="w-4 h-4 rounded-full border-2 border-[#CBD5E1] shrink-0" />
                    )}
                    <span className={
                      analysisProgress === 'results_ready' || analysisProgress === 'completed'
                        ? 'font-semibold text-[#059669]'
                        : 'text-[#64748B]'
                    }>
                      4. Results ready
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Method Selector */}
          <div>
            <h3 className="text-xs font-semibold text-[#142B45] uppercase tracking-wider mb-2">
              Select Intake Method
            </h3>
            <IntakeMethodSelector
              selectedMethod={method}
              onSelectMethod={(m) => {
                if (extractionState === 'analyzing') return;
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
                    'Select a Batch Manufacturing Record (BMR), SCADA excursion report, or deviation memo (PDF).'}
                  {method === 'text' &&
                    'Paste raw operator logs, incident descriptions, or initial QA notification statements.'}
                  {method === 'email' &&
                    'Enter subject line and body of deviation notification email correspondence.'}
                </CardDescription>
              </div>
              <StatusBadge variant="neutral" size="sm">
                Local Input
              </StatusBadge>
            </CardHeader>

            <CardContent>
              {validationError && extractionState !== 'failed' && (
                <div className="p-3 mb-4 bg-[#FEF2F2] border border-[#FECACA] rounded-lg text-xs text-[#991B1B] flex items-center space-x-2">
                  <AlertCircle className="w-4 h-4 shrink-0 text-[#DC2626]" />
                  <span>{validationError}</span>
                </div>
              )}

              {method === 'upload' && (
                <DocumentUpload
                  fileInfo={fileInfo}
                  onFileSelect={(meta, file) => {
                    setSelectedFile(file);
                    dispatch(setIntakeFile(meta));
                  }}
                  onFileRemove={() => {
                    setSelectedFile(null);
                    dispatch(clearIntakeFile());
                  }}
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

            <CardFooter className="py-4 bg-[#F8FAFC] flex items-center justify-between">
              <div className="text-xs text-[#64748B]">
                Intake invokes LangGraph extraction nodes and maps entities into 21 CFR Part 11 deviation records.
              </div>

              <Button
                variant="accent"
                size="md"
                leftIcon={extractionState === 'analyzing' ? Loader2 : Sparkles}
                disabled={extractionState === 'analyzing'}
                onClick={handleAnalyzeIncident}
              >
                {extractionState === 'analyzing' ? 'Analyzing Incident...' : 'Analyze Incident'}
              </Button>
            </CardFooter>
          </Card>
        </div>
      )}

      {/* State D: Structured Extraction Review Experience */}
      {extractionState === 'extracted' && extractedData && (
        <div className="space-y-4">
          {validationError && (
            <div className="p-4 rounded-xl border border-[#FECACA] bg-[#FEF2F2] text-xs text-[#991B1B] flex items-center space-x-2">
              <AlertCircle className="w-5 h-5 shrink-0 text-[#DC2626]" />
              <span className="font-medium">{validationError}</span>
            </div>
          )}
          <ExtractionReviewForm
            extractedData={extractedData}
            onUpdateField={handleUpdateExtractedField}
            onRevertField={handleRevertExtractedField}
            onSaveDraft={handleSaveDraft}
            onContinueToRCA={handleContinueToRCA}
            isDraftSaved={draftSavedToast}
            isSubmitting={isSubmitting}
          />
        </div>
      )}
    </div>
  );
}
