import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../common/Card';
import StatusBadge from '../common/StatusBadge';
import Button from '../common/Button';
import Input from '../common/Input';
import {
  HelpCircle,
  GitCommit,
  CheckCircle2,
  AlertTriangle,
  Save,
  ShieldCheck,
  FileText,
  Info,
  Sparkles,
  Loader2,
  Plus,
  Trash2,
} from 'lucide-react';

const STATUS_OPTIONS = [
  { value: 'AI Suggestion', label: 'AI Suggestion (Hypothesis)' },
  { value: 'Requires Evidence', label: 'Requires Evidence' },
  { value: 'Evidence-Supported', label: 'Evidence-Supported' },
  { value: 'Pending Review', label: 'Pending Human Review' },
  { value: 'Confirmed by Investigator', label: 'Confirmed by Investigator' },
];

/**
 * 5-Whys recursive drilldown component with evidence links, AI generation, and PostgreSQL persistence.
 */
export default function FiveWhysAnalysis({
  fiveWhys = [],
  onSaveLevel,
  onSaveAll,
  onGenerateAI,
  isGenerating = false,
  isSaving = false,
}) {
  const [levels, setLevels] = useState(
    fiveWhys.length > 0
      ? fiveWhys
      : [
          { level: 1, question: 'Why did the incident occur?', answer: '', evidence: '', status: 'Requires Evidence', is_root_cause: false },
          { level: 2, question: 'Why did that condition happen?', answer: '', evidence: '', status: 'Requires Evidence', is_root_cause: false },
          { level: 3, question: 'What caused the previous condition?', answer: '', evidence: '', status: 'Requires Evidence', is_root_cause: false },
          { level: 4, question: 'Why was that cause present?', answer: '', evidence: '', status: 'Requires Evidence', is_root_cause: false },
          { level: 5, question: 'What underlying system or process weakness contributed?', answer: '', evidence: '', status: 'Requires Evidence', is_root_cause: false },
        ]
  );

  const [savedNotification, setSavedNotification] = useState(false);

  useEffect(() => {
    if (fiveWhys && fiveWhys.length > 0) {
      setLevels(fiveWhys);
    }
  }, [fiveWhys]);

  const handleTextChange = (index, field, value) => {
    const updated = [...levels];
    updated[index] = { ...updated[index], [field]: value };
    setLevels(updated);
  };

  const handleStatusChange = (index, newStatus) => {
    const updated = [...levels];
    updated[index] = { ...updated[index], status: newStatus };
    setLevels(updated);
    if (onSaveLevel) {
      onSaveLevel(index, updated[index]);
    }
  };

  const handleToggleRootCause = (index) => {
    const updated = levels.map((lvl, idx) => ({
      ...lvl,
      is_root_cause: idx === index ? !lvl.is_root_cause : false,
    }));
    setLevels(updated);
  };

  const handleSave = async () => {
    if (onSaveAll) {
      await onSaveAll(levels);
    }
    setSavedNotification(true);
    setTimeout(() => setSavedNotification(false), 3000);
  };

  return (
    <div className="space-y-6">
      {/* Pharma Compliance Notice */}
      <div className="p-4 rounded-xl bg-[#EFF6FF] border border-[#BFDBFE] text-xs text-[#1E40AF] flex items-start space-x-3">
        <Info className="w-5 h-5 text-[#2563EB] shrink-0 mt-0.5" />
        <div className="space-y-1">
          <span className="font-bold">GxP Root Cause Verification Standard:</span>
          <p className="leading-relaxed text-[#1E40AF]">
            In pharmaceutical API quality investigations, causal conclusions must never be inferred automatically. Even at Why Level 5, an AI statement remains an unverified hypothesis until empirical physical or analytical evidence is corroborated and confirmed by a certified human investigator.
          </p>
        </div>
      </div>

      {/* Action Header: AI Generation and Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 bg-white rounded-xl border border-[#E2E8F0] shadow-2xs">
        <div>
          <h3 className="text-sm font-bold text-[#142B45]">
            Linear Causal Drilldown (5-Whys Methodology)
          </h3>
          <p className="text-xs text-[#64748B]">
            Recursively investigate physical failure mechanisms to identify systemic root causes.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          {onGenerateAI && (
            <Button
              variant="accent"
              size="sm"
              leftIcon={isGenerating ? Loader2 : Sparkles}
              onClick={onGenerateAI}
              disabled={isGenerating}
            >
              {isGenerating ? 'Running AI Causal Nodes...' : 'Generate AI 5-Whys'}
            </Button>
          )}

          <Button
            variant="primary"
            size="sm"
            leftIcon={Save}
            onClick={handleSave}
            disabled={isSaving || isGenerating}
          >
            {isSaving ? 'Persisting to DB...' : 'Save 5-Whys'}
          </Button>
        </div>
      </div>

      {/* Sequential 5 Whys Chain */}
      <div className="space-y-4">
        {levels.map((item, idx) => {
          const isAnswered = item.answer && item.answer.trim().length > 0;
          const isConfirmed = item.status === 'Confirmed by Investigator';
          const isRootCause = Boolean(item.is_root_cause);

          return (
            <Card
              key={item.level || idx + 1}
              className={`transition-all duration-150 ${
                isRootCause
                  ? 'border-[#0F9D91] ring-2 ring-[#0F9D91]/20 shadow-sm'
                  : isConfirmed
                  ? 'border-[#059669] shadow-xs'
                  : isAnswered
                  ? 'border-[#CBD5E1]'
                  : 'border-[#E2E8F0] bg-[#FAFAFA]'
              }`}
            >
              <CardHeader className="py-3.5 bg-[#F8FAFC]">
                <div className="flex items-center space-x-3">
                  <div
                    className={`w-7 h-7 rounded-full flex items-center justify-center font-mono font-bold text-xs ${
                      isRootCause
                        ? 'bg-[#0F9D91] text-white shadow-2xs'
                        : isConfirmed
                        ? 'bg-[#059669] text-white'
                        : isAnswered
                        ? 'bg-[#142B45] text-white'
                        : 'bg-[#E2E8F0] text-[#64748B]'
                    }`}
                  >
                    W{item.level || idx + 1}
                  </div>
                  <div>
                    <span className="text-xs font-bold text-[#142B45] uppercase tracking-wider">
                      Why Level {item.level || idx + 1} {isRootCause && '• Primary Root Cause'}
                    </span>
                    <h4 className="text-sm font-semibold text-[#142B45]">
                      {item.question}
                    </h4>
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  <span className="text-xs font-medium text-[#64748B] hidden sm:inline">
                    Status:
                  </span>
                  <select
                    value={item.status || 'Requires Evidence'}
                    onChange={(e) => handleStatusChange(idx, e.target.value)}
                    className="text-xs font-medium bg-white border border-[#CBD5E1] rounded-lg px-2.5 py-1 text-[#142B45] focus:outline-none focus:border-[#0F9D91]"
                  >
                    {STATUS_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
              </CardHeader>

              <CardContent className="p-4 sm:p-5 space-y-3">
                {/* Answer Field */}
                <div>
                  <label className="block text-xs font-semibold text-[#142B45] mb-1.5 uppercase tracking-wider">
                    Causal Answer / Finding <span className="text-[#DC2626]">*</span>
                  </label>
                  <textarea
                    rows={2}
                    value={item.answer || ''}
                    onChange={(e) => handleTextChange(idx, 'answer', e.target.value)}
                    placeholder={`State the causal factor identified for Level ${item.level || idx + 1}...`}
                    className="block w-full rounded-lg border border-[#CBD5E1] text-sm p-3 bg-white focus:border-[#0F9D91] focus:ring-2 focus:ring-[#0F9D91]/20 leading-relaxed"
                  />
                </div>

                {/* Supporting Evidence Reference & Root Cause Flag */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                  <div>
                    <label className="block text-xs font-semibold text-[#64748B] mb-1">
                      Supporting Evidence Reference
                    </label>
                    <Input
                      placeholder="e.g. SCADA Tag TIC-102A, HPLC Chromatogram #04"
                      value={item.evidence || ''}
                      onChange={(e) => handleTextChange(idx, 'evidence', e.target.value)}
                      leftIcon={FileText}
                    />
                  </div>

                  <div className="flex items-center justify-between sm:justify-end gap-3 pt-4 sm:pt-0">
                    <label className="inline-flex items-center space-x-2 text-xs font-semibold text-[#142B45] cursor-pointer">
                      <input
                        type="checkbox"
                        checked={Boolean(item.is_root_cause)}
                        onChange={() => handleToggleRootCause(idx)}
                        className="rounded border-[#CBD5E1] text-[#0F9D91] focus:ring-[#0F9D91]/20 w-4 h-4 cursor-pointer"
                      />
                      <span>Designate as Terminal Root Cause</span>
                    </label>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Save Action Footer */}
      <div className="flex items-center justify-between p-4 bg-white rounded-xl border border-[#E2E8F0] shadow-2xs">
        <div className="text-xs text-[#64748B]">
          {savedNotification ? (
            <span className="text-[#059669] font-semibold flex items-center">
              <CheckCircle2 className="w-4 h-4 mr-1" /> 5-Whys Analysis Persisted in Database
            </span>
          ) : (
            <span>Modifications persist transactionally to PostgreSQL adhering to 21 CFR Part 11.</span>
          )}
        </div>

        <Button
          variant="primary"
          size="sm"
          leftIcon={Save}
          onClick={handleSave}
          disabled={isSaving || isGenerating}
        >
          {isSaving ? 'Persisting to DB...' : 'Save 5-Whys Analysis'}
        </Button>
      </div>
    </div>
  );
}
