import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../common/Card';
import Input from '../common/Input';
import Select from '../common/Select';
import StatusBadge from '../common/StatusBadge';
import Button from '../common/Button';
import {
  FileText,
  Sliders,
  AlertTriangle,
  Save,
  ArrowRight,
  Edit3,
  RotateCcw,
  CheckCircle2,
  Info,
  ShieldAlert,
  HelpCircle,
  Activity,
  Layers,
  ChevronDown,
  ChevronUp,
  Tag,
  BookOpen,
  Sparkles,
} from 'lucide-react';

/**
 * Field-level provenance and review input row.
 */
function ReviewField({
  label,
  required,
  value,
  fieldMeta,
  contradiction,
  type = 'text',
  options = [],
  rows = 3,
  disabled = false,
  helperText,
  placeholder,
  onChange,
  onRevert,
}) {
  const [showProvenance, setShowProvenance] = useState(false);

  const isHumanModified = Boolean(fieldMeta?.is_human_modified);
  const confidence = fieldMeta?.confidence_score;
  const confidencePct = typeof confidence === 'number' ? Math.round(confidence * 100) : null;
  const isLowConfidence = typeof confidence === 'number' && confidence < 0.70;
  const sourceRef = fieldMeta?.source_reference;
  const extractionStatus = fieldMeta?.extraction_status || (value ? 'EXTRACTED' : 'MISSING');
  const isMissing = !value || extractionStatus === 'MISSING';
  const warnings = fieldMeta?.validation_warnings || [];

  const isCitationUnverified = Boolean(
    (sourceRef?.excerpt && sourceRef?.is_traceable === false) ||
    warnings.some((w) => typeof w === 'string' && (w.toLowerCase().includes('citation unverified') || w.toLowerCase().includes('could not be matched')))
  );

  const isGeneratedSummary = Boolean(
    extractionStatus === 'INFERRED' &&
    (label?.toLowerCase().includes('title') ||
     warnings.some((w) => typeof w === 'string' && (w.toLowerCase().includes('summary') || w.toLowerCase().includes('synthesized'))))
  );

  return (
    <div className={`p-3.5 rounded-xl border transition-all ${
      contradiction
        ? 'border-[#FCA5A5] bg-[#FEF2F2]/30'
        : isHumanModified
        ? 'border-[#C7D2FE] bg-[#EEF2FF]/20'
        : isCitationUnverified
        ? 'border-[#FDE68A] bg-[#FFFBEB]/30'
        : isLowConfidence
        ? 'border-[#FDE68A] bg-[#FFFBEB]/20'
        : isMissing
        ? 'border-[#E2E8F0] bg-[#F8FAFC]'
        : 'border-[#E2E8F0] bg-white'
    }`}>
      {/* Field Header: Label & Provenance Badges */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
        <label className="block text-xs font-bold text-[#142B45] uppercase tracking-wider">
          {label} {required && <span className="text-[#DC2626]">*</span>}
        </label>

        <div className="flex items-center space-x-1.5 flex-wrap gap-y-1">
          {/* Status Badge */}
          {isHumanModified ? (
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-[#EEF2FF] text-[#4338CA] border border-[#C7D2FE]">
              <Edit3 className="w-2.5 h-2.5 mr-1" />
              Edited
            </span>
          ) : isMissing ? (
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-[#F1F5F9] text-[#64748B] border border-[#CBD5E1]">
              Missing
            </span>
          ) : isGeneratedSummary ? (
            <span
              className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-[#F3E8FF] text-[#6B21A8] border border-[#E9D5FF]"
              title="AI-generated summary title synthesized from incident description — not explicitly titled in source document."
            >
              <Sparkles className="w-2.5 h-2.5 mr-1 text-[#9333EA]" />
              AI Generated Summary
            </span>
          ) : extractionStatus === 'INFERRED' ? (
            <span
              className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-[#FEF3C7] text-[#92400E] border border-[#FDE68A]"
              title={warnings.length ? warnings[0] : 'Inferred from contextual evidence — requires investigator review'}
            >
              <HelpCircle className="w-2.5 h-2.5 mr-1" />
              Inferred
            </span>
          ) : extractionStatus === 'AMBIGUOUS' ? (
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-[#FEF3C7] text-[#92400E] border border-[#FDE68A]">
              Ambiguous
            </span>
          ) : (
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-[#E6F7F5] text-[#0F9D91] border border-[#A7F3D0]">
              AI Extracted
            </span>
          )}

          {/* Citation Verification Status Badge */}
          {isCitationUnverified ? (
            <span
              className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-[#FEF3C7] text-[#92400E] border border-[#FDE68A]"
              title="The cited excerpt could not be matched at reported character offsets in the source text. Manual verification by an investigator is required."
            >
              <AlertTriangle className="w-2.5 h-2.5 mr-1 text-[#D97706]" />
              Citation unverified — investigator review required
            </span>
          ) : sourceRef?.is_traceable && !isMissing ? (
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-[#ECFDF5] text-[#065F46] border border-[#A7F3D0]">
              <CheckCircle2 className="w-2.5 h-2.5 mr-1 text-[#059669]" />
              Citation Verified
            </span>
          ) : null}

          {/* Confidence Badge (Heuristic model confidence, clearly separated from verified evidence) */}
          {confidencePct !== null && (
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold border ${
                isCitationUnverified
                  ? 'bg-[#FEF3C7] text-[#92400E] border-[#FDE68A]'
                  : isLowConfidence
                  ? 'bg-[#FEF3C7] text-[#B45309] border-[#FDE68A]'
                  : 'bg-[#F0FDF4] text-[#15803D] border-[#BBF7D0]'
              }`}
              title={`Confidence score heuristic: ${confidence}`}
            >
              {isCitationUnverified ? `Confidence: ${Math.min(confidencePct, 70)}% (Unverified Citation)` : isLowConfidence ? `Low: ${confidencePct}%` : `${confidencePct}%`}
            </span>
          )}

          {/* Contradiction Warning Badge */}
          {contradiction && (
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-[#FEE2E2] text-[#991B1B] border border-[#FECACA]">
              <AlertTriangle className="w-2.5 h-2.5 mr-1" />
              Contradiction
            </span>
          )}

          {/* Source Citation Toggle */}
          {sourceRef?.excerpt && (
            <button
              type="button"
              onClick={() => setShowProvenance(!showProvenance)}
              className="inline-flex items-center text-[10px] font-medium text-[#0F9D91] hover:text-[#0C7C73] underline ml-1 cursor-pointer"
              title="View verbatim citation in source intake"
            >
              <BookOpen className="w-2.5 h-2.5 mr-0.5" />
              {showProvenance ? 'Hide citation' : 'View citation'}
            </button>
          )}

          {/* Revert to AI Button */}
          {isHumanModified && onRevert && (
            <button
              type="button"
              onClick={onRevert}
              className="inline-flex items-center text-[10px] font-medium text-[#4338CA] hover:text-[#3730A3] underline ml-1 cursor-pointer"
              title="Discard human modifications and revert to AI-extracted value"
            >
              <RotateCcw className="w-2.5 h-2.5 mr-0.5" />
              Revert to AI
            </button>
          )}
        </div>
      </div>

      {/* Contradiction Alert Box */}
      {contradiction && (
        <div className="mb-2 p-2 rounded-lg bg-[#FEF2F2] border border-[#FCA5A5] text-xs text-[#991B1B] space-y-1">
          <div className="flex items-center space-x-1 font-semibold">
            <ShieldAlert className="w-3.5 h-3.5 text-[#DC2626]" />
            <span>Conflicting evidence detected in narrative:</span>
          </div>
          <p className="text-[11px] leading-relaxed">{contradiction.description}</p>
          {contradiction.conflicting_values?.length > 0 && (
            <div className="text-[11px] font-mono text-[#7F1D1D] bg-white/70 p-1 rounded border border-[#FECACA]">
              Found candidates: {contradiction.conflicting_values.join(' vs ')}
            </div>
          )}
        </div>
      )}

      {/* Verbatim Source Citation Dropdown */}
      {showProvenance && sourceRef?.excerpt && (
        <div className="mb-2.5 p-2.5 rounded-lg bg-[#F8FAFC] border border-[#CBD5E1] text-xs space-y-1.5">
          <div className="flex items-center justify-between text-[11px] font-semibold text-[#142B45]">
            <span className="flex items-center">
              <BookOpen className="w-3 h-3 mr-1 text-[#0F9D91]" />
              Source Intake Evidence
            </span>
            <div className="flex items-center space-x-2">
              {isCitationUnverified ? (
                <span className="text-[10px] text-[#92400E] font-medium flex items-center">
                  <AlertTriangle className="w-2.5 h-2.5 mr-0.5 text-[#D97706]" />
                  Unverified Offsets
                </span>
              ) : sourceRef.is_traceable ? (
                <span className="text-[10px] text-[#065F46] font-medium flex items-center">
                  <CheckCircle2 className="w-2.5 h-2.5 mr-0.5 text-[#059669]" />
                  Verified in Source
                </span>
              ) : null}
              <span className="text-[#64748B]">
                {sourceRef.source_type || 'Narrative'}
                {sourceRef.page_number ? ` • Page ${sourceRef.page_number}` : ''}
              </span>
            </div>
          </div>
          {isCitationUnverified && (
            <div className="p-2 rounded bg-[#FFFBEB] border border-[#FDE68A] text-[11px] text-[#92400E] flex items-center space-x-1.5">
              <AlertCircle className="w-3.5 h-3.5 text-[#D97706] shrink-0" />
              <span>Citation unverified — investigator review required. The cited excerpt could not be matched at reported character offsets in the source text.</span>
            </div>
          )}
          <blockquote className="p-1.5 bg-white rounded border border-[#E2E8F0] text-[11px] italic text-[#334155] leading-relaxed">
            &ldquo;{sourceRef.excerpt}&rdquo;
          </blockquote>
        </div>
      )}

      {/* Original AI Value Notice if modified */}
      {isHumanModified && fieldMeta?.ai_extracted_value !== undefined && (
        <div className="mb-2 text-[11px] text-[#64748B] flex items-center space-x-1.5">
          <span className="font-semibold text-[#4338CA]">Original AI Value:</span>
          <span className="italic truncate max-w-md">
            {fieldMeta.ai_extracted_value !== null ? String(fieldMeta.ai_extracted_value) : '(empty)'}
          </span>
        </div>
      )}

      {/* Field Input Control */}
      {type === 'select' ? (
        <select
          value={value || ''}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          className="block w-full rounded-lg border border-[#CBD5E1] text-sm p-2.5 bg-white focus:border-[#0F9D91] focus:ring-2 focus:ring-[#0F9D91]/20 disabled:bg-[#F8FAFC] disabled:text-[#64748B]"
        >
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      ) : type === 'textarea' ? (
        <textarea
          rows={rows}
          value={value || ''}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          placeholder={placeholder || `Enter ${label.toLowerCase()}...`}
          className="block w-full rounded-lg border border-[#CBD5E1] text-sm p-2.5 bg-white leading-relaxed focus:border-[#0F9D91] focus:ring-2 focus:ring-[#0F9D91]/20 disabled:bg-[#F8FAFC] disabled:text-[#64748B]"
        />
      ) : (
        <input
          type="text"
          value={value || ''}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          placeholder={placeholder || `Enter ${label.toLowerCase()}...`}
          className="block w-full rounded-lg border border-[#CBD5E1] text-sm p-2.5 bg-white focus:border-[#0F9D91] focus:ring-2 focus:ring-[#0F9D91]/20 disabled:bg-[#F8FAFC] disabled:text-[#64748B]"
        />
      )}

      {/* Validation Warnings */}
      {warnings.length > 0 && (
        <div className="mt-1.5 space-y-0.5">
          {warnings.map((warn, i) => (
            <p key={i} className="text-[11px] text-[#DC2626] flex items-center">
              <span className="mr-1">&bull;</span> {warn}
            </p>
          ))}
        </div>
      )}

      {helperText && !warnings.length && (
        <p className="text-[11px] text-[#64748B] mt-1">{helperText}</p>
      )}
    </div>
  );
}

/**
 * Enterprise GxP Investigation Extraction Review Form.
 * Presents field-level confidence scores, citations, human editing with AI revert,
 * regulatory critical gaps, and contradiction resolution.
 */
export default function ExtractionReviewForm({
  extractedData,
  onUpdateField,
  onRevertField,
  onSaveDraft,
  onContinueToRCA,
  isDraftSaved,
  isSubmitting = false,
}) {
  const [isEditing, setIsEditing] = useState(true);
  const [showCriticalGaps, setShowCriticalGaps] = useState(true);
  const [showContradictions, setShowContradictions] = useState(true);
  const [showQuestions, setShowQuestions] = useState(true);

  if (!extractedData) return null;

  const {
    incidentInfo = {},
    context = {},
    additionalContext = {},
    fieldMeta = {},
    completenessScore = 0,
    overallConfidence = 0,
    criticalGaps = [],
    possibleContradictions = [],
    investigatorQuestions = [],
    extractionWarnings = [],
    extractionStatus = 'NEEDS_REVIEW',
    disclaimer,
  } = extractedData;

  const getContradictionForField = (fieldName) => {
    return (possibleContradictions || []).find(
      (c) => c.field_name === fieldName || c.field_name === fieldName.replace('_id', '')
    );
  };

  const completenessPct = Math.round(completenessScore);
  const confidencePct = Math.round(overallConfidence * 100);

  return (
    <div className="space-y-6">
      {/* 1. Mandatory GxP Non-Repudiation Notice */}
      <div className="p-4 rounded-xl bg-[#FFFBEB] border border-[#FDE68A] text-xs text-[#92400E] shadow-2xs space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2 font-bold text-sm text-[#B45309]">
            <AlertTriangle className="w-4 h-4 text-[#D97706]" />
            <span>AI-Assisted Intake Extraction &bull; Human Verification Required</span>
          </div>
          <StatusBadge
            variant={
              extractionStatus === 'COMPLETED'
                ? 'success'
                : extractionStatus === 'FAILED'
                ? 'danger'
                : 'warning'
            }
            size="sm"
          >
            {extractionStatus === 'COMPLETED'
              ? 'Complete Extraction'
              : extractionStatus === 'FAILED'
              ? 'Extraction Needs Attention'
              : 'Pending Human Review'}
          </StatusBadge>
        </div>
        <p className="leading-relaxed text-[#92400E]">
          {disclaimer ||
            'AI-extracted fields are machine suggestions derived from unstructured intake text. 21 CFR Part 11 and EU GMP Annex 11 require qualified human verification before proceeding to formal Root Cause Analysis.'}
        </p>
      </div>

      {/* 2. Top Metric Cards Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-white p-3.5 rounded-xl border border-[#E2E8F0] shadow-2xs">
          <div className="text-[11px] font-semibold text-[#64748B] uppercase tracking-wider">
            Completeness
          </div>
          <div className="mt-1 flex items-baseline space-x-1.5">
            <span className="text-xl font-bold text-[#142B45]">{completenessPct}%</span>
            <span className="text-[11px] text-[#64748B]">source coverage</span>
          </div>
          <div className="mt-2 w-full bg-[#E2E8F0] h-1.5 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                completenessPct >= 75
                  ? 'bg-[#0F9D91]'
                  : completenessPct >= 50
                  ? 'bg-[#D97706]'
                  : 'bg-[#DC2626]'
              }`}
              style={{ width: `${Math.min(completenessPct, 100)}%` }}
            />
          </div>
        </div>

        <div className="bg-white p-3.5 rounded-xl border border-[#E2E8F0] shadow-2xs">
          <div className="text-[11px] font-semibold text-[#64748B] uppercase tracking-wider">
            Average Confidence
          </div>
          <div className="mt-1 flex items-baseline space-x-1.5">
            <span className="text-xl font-bold text-[#142B45]">{confidencePct}%</span>
            <span className="text-[11px] text-[#64748B]">heuristic</span>
          </div>
          <div className="mt-2 w-full bg-[#E2E8F0] h-1.5 rounded-full overflow-hidden">
            <div
              className="h-full bg-[#059669] rounded-full transition-all duration-500"
              style={{ width: `${Math.min(confidencePct, 100)}%` }}
            />
          </div>
        </div>

        <div className="bg-white p-3.5 rounded-xl border border-[#E2E8F0] shadow-2xs">
          <div className="text-[11px] font-semibold text-[#64748B] uppercase tracking-wider">
            Critical Gaps
          </div>
          <div className="mt-1 flex items-baseline space-x-1.5">
            <span
              className={`text-xl font-bold ${
                criticalGaps.length > 0 ? 'text-[#DC2626]' : 'text-[#059669]'
              }`}
            >
              {criticalGaps.length}
            </span>
            <span className="text-[11px] text-[#64748B]">mandatory items</span>
          </div>
          <div className="mt-2 text-[10px] text-[#64748B] truncate">
            {criticalGaps.length > 0
              ? `${criticalGaps.length} GxP gap(s) to address`
              : 'All mandatory fields present'}
          </div>
        </div>

        <div className="bg-white p-3.5 rounded-xl border border-[#E2E8F0] shadow-2xs">
          <div className="text-[11px] font-semibold text-[#64748B] uppercase tracking-wider">
            Contradictions
          </div>
          <div className="mt-1 flex items-baseline space-x-1.5">
            <span
              className={`text-xl font-bold ${
                possibleContradictions.length > 0 ? 'text-[#D97706]' : 'text-[#059669]'
              }`}
            >
              {possibleContradictions.length}
            </span>
            <span className="text-[11px] text-[#64748B]">identified</span>
          </div>
          <div className="mt-2 text-[10px] text-[#64748B] truncate">
            {possibleContradictions.length > 0
              ? 'Conflicts in intake source'
              : 'No contradictory values'}
          </div>
        </div>
      </div>

      {/* 3. Global Extraction Warnings Banner (if any) */}
      {extractionWarnings.length > 0 && (
        <div className="p-3.5 rounded-xl bg-[#FEF2F2] border border-[#FECACA] text-xs text-[#991B1B] space-y-1">
          <div className="flex items-center space-x-1.5 font-bold">
            <AlertTriangle className="w-4 h-4 text-[#DC2626]" />
            <span>Intake Extraction Processing Warnings</span>
          </div>
          <ul className="list-disc list-inside space-y-0.5 text-[11px] pl-1">
            {extractionWarnings.map((warn, i) => (
              <li key={i}>{warn}</li>
            ))}
          </ul>
        </div>
      )}

      {/* 4. Action Controls Bar */}
      <div className="flex items-center justify-between bg-white p-4 rounded-xl border border-[#E2E8F0] shadow-2xs">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-[#E6F7F5] text-[#0F9D91] flex items-center justify-center font-bold text-xs">
            1
          </div>
          <div>
            <h3 className="text-sm font-bold text-[#142B45]">
              Verify Extracted Deviation Record
            </h3>
            <p className="text-xs text-[#64748B]">
              Review AI extractions, resolve gaps, and confirm parameters prior to RCA.
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2.5">
          <Button
            variant={isEditing ? 'secondary' : 'outline'}
            size="sm"
            leftIcon={Edit3}
            onClick={() => setIsEditing(!isEditing)}
          >
            {isEditing ? 'Lock for Preview' : 'Enable Editing'}
          </Button>

          <Button
            variant="secondary"
            size="sm"
            leftIcon={Save}
            onClick={onSaveDraft}
          >
            {isDraftSaved ? 'Draft Saved Locally' : 'Save Draft'}
          </Button>

          <Button
            variant="accent"
            size="sm"
            rightIcon={ArrowRight}
            onClick={onContinueToRCA}
            disabled={isSubmitting}
          >
            {isSubmitting ? 'Creating Investigation...' : 'Continue to RCA'}
          </Button>
        </div>
      </div>

      {/* 5. Collapsible Critical Gaps Panel */}
      {criticalGaps.length > 0 && (
        <Card className="border-[#FECACA]">
          <CardHeader
            className="cursor-pointer bg-[#FEF2F2]/40 py-3"
            onClick={() => setShowCriticalGaps(!showCriticalGaps)}
          >
            <div className="flex items-center justify-between w-full">
              <div className="flex items-center space-x-2 text-[#991B1B]">
                <ShieldAlert className="w-4 h-4 text-[#DC2626]" />
                <span className="font-bold text-xs uppercase tracking-wider">
                  Critical GxP Evidence Gaps ({criticalGaps.length})
                </span>
              </div>
              <div className="flex items-center space-x-2">
                <span className="text-[11px] text-[#991B1B]">Mandatory for deviation closure</span>
                {showCriticalGaps ? (
                  <ChevronUp className="w-4 h-4 text-[#991B1B]" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-[#991B1B]" />
                )}
              </div>
            </div>
          </CardHeader>
          {showCriticalGaps && (
            <CardContent className="space-y-2 pt-3">
              {criticalGaps.map((gap, i) => (
                <div
                  key={i}
                  className="p-3 rounded-lg bg-white border border-[#FECACA] text-xs space-y-1"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-[#142B45] font-mono text-[11px]">
                      {typeof gap === 'string' ? gap : gap.field_name}
                    </span>
                    <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-[#FEE2E2] text-[#991B1B]">
                      {typeof gap === 'object' && gap.category ? gap.category : 'Critical GxP'}
                    </span>
                  </div>
                  {typeof gap === 'object' && gap.rationale && (
                    <p className="text-[11px] text-[#64748B] leading-relaxed">
                      <strong>Regulatory Rationale:</strong> {gap.rationale}
                    </p>
                  )}
                  {typeof gap === 'object' && gap.suggested_action && (
                    <p className="text-[11px] text-[#0F9D91] leading-relaxed font-medium">
                      <strong>Recommended Action:</strong> {gap.suggested_action}
                    </p>
                  )}
                </div>
              ))}
            </CardContent>
          )}
        </Card>
      )}

      {/* 6. Collapsible Contradictions Panel */}
      {possibleContradictions.length > 0 && (
        <Card className="border-[#FDE68A]">
          <CardHeader
            className="cursor-pointer bg-[#FFFBEB]/50 py-3"
            onClick={() => setShowContradictions(!showContradictions)}
          >
            <div className="flex items-center justify-between w-full">
              <div className="flex items-center space-x-2 text-[#92400E]">
                <AlertTriangle className="w-4 h-4 text-[#D97706]" />
                <span className="font-bold text-xs uppercase tracking-wider">
                  Conflicting Source Statements ({possibleContradictions.length})
                </span>
              </div>
              <div className="flex items-center space-x-2">
                <span className="text-[11px] text-[#92400E]">Investigator review required</span>
                {showContradictions ? (
                  <ChevronUp className="w-4 h-4 text-[#92400E]" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-[#92400E]" />
                )}
              </div>
            </div>
          </CardHeader>
          {showContradictions && (
            <CardContent className="space-y-2 pt-3">
              {possibleContradictions.map((c, i) => (
                <div
                  key={i}
                  className="p-3 rounded-lg bg-white border border-[#FDE68A] text-xs space-y-1.5"
                >
                  <div className="flex items-center justify-between font-bold text-[#142B45]">
                    <span className="font-mono text-[11px]">Field: {c.field_name}</span>
                    <span className="text-[10px] text-[#D97706] font-normal">
                      Status: {c.resolution_status || 'INVESTIGATOR_REVIEW_REQUIRED'}
                    </span>
                  </div>
                  <p className="text-[11px] text-[#64748B] leading-relaxed">{c.description}</p>
                  {c.conflicting_values?.length > 0 && (
                    <div className="p-1.5 bg-[#FFFBEB] rounded border border-[#FDE68A] text-[11px] font-mono text-[#92400E]">
                      Candidates: {c.conflicting_values.join('  ⚡  ')}
                    </div>
                  )}
                </div>
              ))}
            </CardContent>
          )}
        </Card>
      )}

      {/* 7. Collapsible Targeted Investigator Questions Panel */}
      {investigatorQuestions.length > 0 && (
        <Card className="border-[#CBD5E1]">
          <CardHeader
            className="cursor-pointer bg-[#F8FAFC] py-3"
            onClick={() => setShowQuestions(!showQuestions)}
          >
            <div className="flex items-center justify-between w-full">
              <div className="flex items-center space-x-2 text-[#142B45]">
                <HelpCircle className="w-4 h-4 text-[#0F9D91]" />
                <span className="font-bold text-xs uppercase tracking-wider">
                  Targeted Investigator Follow-Up Questions ({investigatorQuestions.length})
                </span>
              </div>
              <div className="flex items-center space-x-2">
                <span className="text-[11px] text-[#64748B]">Derived from missing evidence</span>
                {showQuestions ? (
                  <ChevronUp className="w-4 h-4 text-[#64748B]" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-[#64748B]" />
                )}
              </div>
            </div>
          </CardHeader>
          {showQuestions && (
            <CardContent className="pt-3">
              <ul className="space-y-1.5 text-xs text-[#334155]">
                {investigatorQuestions.map((q, i) => (
                  <li key={i} className="flex items-start space-x-2 p-2 rounded-lg bg-[#F8FAFC]">
                    <span className="w-5 h-5 rounded-full bg-[#E6F7F5] text-[#0F9D91] font-bold text-[10px] flex items-center justify-center shrink-0 mt-0.5">
                      {i + 1}
                    </span>
                    <span className="leading-relaxed">{q}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          )}
        </Card>
      )}

      {/* Section 1: Incident Information */}
      <Card>
        <CardHeader>
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#142B45] text-white flex items-center justify-center">
              <FileText className="w-4 h-4 text-[#0F9D91]" />
            </div>
            <div>
              <CardTitle>Section 1: Incident Information</CardTitle>
              <CardDescription>
                Core event identifiers, manufacturing equipment, and timestamps
              </CardDescription>
            </div>
          </div>
          <StatusBadge variant="neutral" size="sm">
            {isEditing ? 'Editable Mode' : 'Read-Only Preview'}
          </StatusBadge>
        </CardHeader>

        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <ReviewField
              label="Deviation ID"
              value={incidentInfo.deviationId}
              fieldMeta={fieldMeta.deviation_id}
              contradiction={getContradictionForField('deviation_id')}
              disabled={!isEditing}
              placeholder="e.g. DEV-2026-0891"
              required
              onChange={(val) => onUpdateField('incidentInfo', 'deviationId', val, 'deviation_id')}
              onRevert={onRevertField ? () => onRevertField('incidentInfo', 'deviationId', 'deviation_id') : null}
            />

            <ReviewField
              label="Batch Number"
              value={incidentInfo.batchNumber}
              fieldMeta={fieldMeta.batch_number}
              contradiction={getContradictionForField('batch_number')}
              disabled={!isEditing}
              placeholder="e.g. BATCH-2026-9921"
              required
              onChange={(val) => onUpdateField('incidentInfo', 'batchNumber', val, 'batch_number')}
              onRevert={onRevertField ? () => onRevertField('incidentInfo', 'batchNumber', 'batch_number') : null}
            />

            <ReviewField
              label="Deviation Severity"
              value={incidentInfo.severity || ''}
              fieldMeta={fieldMeta.severity || {
                is_human_modified: false,
                confidence_score: null,
                extraction_status: 'MISSING',
                validation_warnings: ['Deviation severity not specified in source document — formal investigator assessment required.'],
              }}
              type="select"
              options={[
                { value: '', label: '-- Select Severity (Investigator Assessment Required) --' },
                { value: 'Critical', label: 'Critical (Disposition Impact)' },
                { value: 'High', label: 'High (Process Excursion)' },
                { value: 'Medium', label: 'Medium (Minor OOS / Yield)' },
                { value: 'Low', label: 'Low (Documentation / Non-critical)' },
              ]}
              disabled={!isEditing}
              required
              helperText={!incidentInfo.severity ? 'Investigator assessment required prior to continuing to RCA.' : undefined}
              onChange={(val) => onUpdateField('incidentInfo', 'severity', val, 'severity')}
            />
          </div>

          <ReviewField
            label="Incident Title"
            value={incidentInfo.incidentTitle}
            fieldMeta={fieldMeta.incident_title}
            contradiction={getContradictionForField('incident_title')}
            disabled={!isEditing}
            placeholder="Concise summary of deviation or excursion"
            required
            onChange={(val) => onUpdateField('incidentInfo', 'incidentTitle', val, 'incident_title')}
            onRevert={onRevertField ? () => onRevertField('incidentInfo', 'incidentTitle', 'incident_title') : null}
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <ReviewField
              label="Product / Formulation Name"
              value={incidentInfo.productName}
              fieldMeta={fieldMeta.product_name}
              contradiction={getContradictionForField('product_name')}
              disabled={!isEditing}
              placeholder="e.g. Atorvastatin Calcium API"
              required
              onChange={(val) => onUpdateField('incidentInfo', 'productName', val, 'product_name')}
              onRevert={onRevertField ? () => onRevertField('incidentInfo', 'productName', 'product_name') : null}
            />

            <ReviewField
              label="Department / Area"
              value={incidentInfo.department}
              fieldMeta={fieldMeta.department}
              contradiction={getContradictionForField('department')}
              disabled={!isEditing}
              placeholder="e.g. Chemical Synthesis Unit"
              required
              onChange={(val) => onUpdateField('incidentInfo', 'department', val, 'department')}
              onRevert={onRevertField ? () => onRevertField('incidentInfo', 'department', 'department') : null}
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <ReviewField
              label="Equipment / Machinery Tag"
              value={incidentInfo.equipment}
              fieldMeta={fieldMeta.equipment_id}
              contradiction={getContradictionForField('equipment_id')}
              disabled={!isEditing}
              placeholder="e.g. R-102"
              required
              onChange={(val) => onUpdateField('incidentInfo', 'equipment', val, 'equipment_id')}
              onRevert={onRevertField ? () => onRevertField('incidentInfo', 'equipment', 'equipment_id') : null}
            />

            <ReviewField
              label="Incident Date"
              value={incidentInfo.incidentDate}
              fieldMeta={fieldMeta.incident_date}
              contradiction={getContradictionForField('incident_date')}
              disabled={!isEditing}
              placeholder="YYYY-MM-DD"
              helperText="Date excursion physically occurred"
              required
              onChange={(val) => onUpdateField('incidentInfo', 'incidentDate', val, 'incident_date')}
              onRevert={onRevertField ? () => onRevertField('incidentInfo', 'incidentDate', 'incident_date') : null}
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <ReviewField
              label="Detection Method / Mechanism"
              value={additionalContext.detectionMethod}
              fieldMeta={fieldMeta.detection_method}
              contradiction={getContradictionForField('detection_method')}
              disabled={!isEditing}
              placeholder="e.g. SCADA Temperature Alarm, Shift Log, In-Process Control (IPC)"
              helperText="Mechanism or instrument through which deviation was identified"
              onChange={(val) => onUpdateField('additionalContext', 'detectionMethod', val, 'detection_method')}
              onRevert={onRevertField ? () => onRevertField('additionalContext', 'detectionMethod', 'detection_method') : null}
            />

            <ReviewField
              label="Detection Date"
              value={incidentInfo.detectionDate}
              fieldMeta={fieldMeta.detection_date}
              contradiction={getContradictionForField('detection_date')}
              disabled={!isEditing}
              placeholder="YYYY-MM-DD"
              helperText="Date excursion was first detected"
              required
              onChange={(val) => onUpdateField('incidentInfo', 'detectionDate', val, 'detection_date')}
              onRevert={onRevertField ? () => onRevertField('incidentInfo', 'detectionDate', 'detection_date') : null}
            />
          </div>

          <ReviewField
            label="Incident Description"
            value={incidentInfo.incidentDescription}
            fieldMeta={fieldMeta.incident_description}
            contradiction={getContradictionForField('incident_description')}
            type="textarea"
            rows={3}
            disabled={!isEditing}
            placeholder="Comprehensive narrative detailing observed excursion..."
            required
            onChange={(val) => onUpdateField('incidentInfo', 'incidentDescription', val, 'incident_description')}
            onRevert={onRevertField ? () => onRevertField('incidentInfo', 'incidentDescription', 'incident_description') : null}
          />

          <ReviewField
            label="Immediate Action Taken (Containment)"
            value={incidentInfo.immediateActionTaken}
            fieldMeta={fieldMeta.immediate_action_taken}
            contradiction={getContradictionForField('immediate_action_taken')}
            type="textarea"
            rows={2}
            disabled={!isEditing}
            placeholder="Containment measures taken immediately upon detection..."
            onChange={(val) => onUpdateField('incidentInfo', 'immediateActionTaken', val, 'immediate_action_taken')}
            onRevert={onRevertField ? () => onRevertField('incidentInfo', 'immediateActionTaken', 'immediate_action_taken') : null}
          />
        </CardContent>
      </Card>

      {/* Section 2: Investigation Context & Observations */}
      <Card>
        <CardHeader>
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#0F9D91]/10 text-[#0F9D91] flex items-center justify-center">
              <Sliders className="w-4 h-4 text-[#0F9D91]" />
            </div>
            <div>
              <CardTitle>Section 2: Investigation Context & Observations</CardTitle>
              <CardDescription>
                Process conditions, observed impact, and baseline operational specs
              </CardDescription>
            </div>
          </div>
          <StatusBadge variant="teal" size="sm">
            Contextual Signals
          </StatusBadge>
        </CardHeader>

        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <ReviewField
              label="Expected Condition (SOP Limit)"
              value={context.expectedCondition}
              fieldMeta={fieldMeta.expected_condition}
              contradiction={getContradictionForField('expected_condition')}
              disabled={!isEditing}
              placeholder="e.g. 65.0 - 70.0 °C at 350 RPM"
              required
              onChange={(val) => onUpdateField('context', 'expectedCondition', val, 'expected_condition')}
              onRevert={onRevertField ? () => onRevertField('context', 'expectedCondition', 'expected_condition') : null}
            />

            <ReviewField
              label="Actual Condition (Observed Excursion)"
              value={context.actualCondition}
              fieldMeta={fieldMeta.actual_condition}
              contradiction={getContradictionForField('actual_condition')}
              disabled={!isEditing}
              placeholder="e.g. Temperature reached 84.5 °C"
              required
              onChange={(val) => onUpdateField('context', 'actualCondition', val, 'actual_condition')}
              onRevert={onRevertField ? () => onRevertField('context', 'actualCondition', 'actual_condition') : null}
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <ReviewField
              label="Observed Impact on Batch / Quality"
              value={context.observedImpact}
              fieldMeta={fieldMeta.potential_impact}
              contradiction={getContradictionForField('potential_impact')}
              disabled={!isEditing}
              placeholder="e.g. Slurry discoloration, potential thermal degradation (if assessed)"
              required={false}
              helperText="Record if evaluated; leave empty if impact assessment is still pending"
              onChange={(val) => onUpdateField('context', 'observedImpact', val, 'potential_impact')}
              onRevert={onRevertField ? () => onRevertField('context', 'observedImpact', 'potential_impact') : null}
            />

            <ReviewField
              label="Affected Process Stage"
              value={context.affectedProcess}
              fieldMeta={fieldMeta.process_stage}
              contradiction={getContradictionForField('process_stage')}
              disabled={!isEditing}
              placeholder="e.g. Stage 3 Crystallization"
              required
              onChange={(val) => onUpdateField('context', 'affectedProcess', val, 'process_stage')}
              onRevert={onRevertField ? () => onRevertField('context', 'affectedProcess', 'process_stage') : null}
            />
          </div>

          <ReviewField
            label="Initial Observations & Telemetry Signals"
            value={context.initialObservations}
            fieldMeta={fieldMeta.observations}
            contradiction={getContradictionForField('observations')}
            type="textarea"
            rows={2}
            disabled={!isEditing}
            placeholder="Preliminary operator notes, SCADA readings, visual cues..."
            onChange={(val) => onUpdateField('context', 'initialObservations', val, 'observations')}
            onRevert={onRevertField ? () => onRevertField('context', 'initialObservations', 'observations') : null}
          />
        </CardContent>

        <CardFooter className="flex items-center justify-between">
          <div className="flex items-center text-xs text-[#64748B]">
            <Info className="w-3.5 h-3.5 mr-1 text-[#0F9D91]" />
            Reviewing and confirming these fields seeds the formal RCA causal tree.
          </div>

          <div className="flex items-center space-x-2">
            <Button
              variant="secondary"
              size="sm"
              leftIcon={Save}
              onClick={onSaveDraft}
            >
              {isDraftSaved ? 'Draft Saved Locally' : 'Save Draft'}
            </Button>
            <Button
              variant="accent"
              size="sm"
              rightIcon={ArrowRight}
              onClick={onContinueToRCA}
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Creating Investigation...' : 'Continue to RCA'}
            </Button>
          </div>
        </CardFooter>
      </Card>
    </div>
  );
}
