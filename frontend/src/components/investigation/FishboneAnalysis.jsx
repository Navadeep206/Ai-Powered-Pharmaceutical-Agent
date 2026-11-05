import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../common/Card';
import StatusBadge from '../common/StatusBadge';
import Button from '../common/Button';
import Input from '../common/Input';
import {
  Users,
  Cpu,
  FileCode,
  Box,
  Scale,
  CloudRain,
  Plus,
  Trash2,
  AlertCircle,
  HelpCircle,
  CheckCircle,
  CheckCircle2,
  Sparkles,
  Save,
  Loader2,
} from 'lucide-react';

const CATEGORY_META = {
  Manpower: {
    label: 'Manpower (People)',
    icon: Users,
    description: 'Training, shift handover, operator technique, fatigue',
    color: 'text-[#142B45]',
    bg: 'bg-[#142B45]/5',
  },
  Machine: {
    label: 'Machine (Equipment)',
    icon: Cpu,
    description: 'Valves, actuators, reactor seals, pumps, PLC sensors',
    color: 'text-[#0F9D91]',
    bg: 'bg-[#E6F7F5]',
  },
  Method: {
    label: 'Method (Procedures)',
    icon: FileCode,
    description: 'Batch record SOPs, sampling protocols, mixing time',
    color: 'text-[#2563EB]',
    bg: 'bg-[#EFF6FF]',
  },
  Material: {
    label: 'Material (Reagents)',
    icon: Box,
    description: 'Raw material lots, solvent purity, moisture content, CoA',
    color: 'text-[#D97706]',
    bg: 'bg-[#FFFBEB]',
  },
  Measurement: {
    label: 'Measurement (Testing)',
    icon: Scale,
    description: 'HPLC calibration, RTD sensors, pH probe calibration drift',
    color: 'text-[#7C3AED]',
    bg: 'bg-[#F5F3FF]',
  },
  Environment: {
    label: 'Environment (Milieu)',
    icon: CloudRain,
    description: 'Cleanroom humidity, HVAC differential pressure, temp',
    color: 'text-[#059669]',
    bg: 'bg-[#ECFDF5]',
  },
};

const STATUS_TAGS = {
  'AI Suggestion': { variant: 'teal', label: 'AI Suggestion' },
  'Requires Evidence': { variant: 'warning', label: 'Requires Evidence' },
  'Pending Review': { variant: 'info', label: 'Pending Review' },
  'Evidence-Supported': { variant: 'info', label: 'Evidence-Supported' },
  'Confirmed by Investigator': { variant: 'success', label: 'Confirmed Cause' },
};

/**
 * 6M Ishikawa (Fishbone) Causal Analysis Interface with AI generation and PostgreSQL persistence.
 */
export default function FishboneAnalysis({
  fishbone = {},
  onAddCause,
  onUpdateCauseStatus,
  onRemoveCause,
  onSaveAll,
  onGenerateAI,
  isGenerating = false,
  isSaving = false,
}) {
  const [activeAddCategory, setActiveAddCategory] = useState(null);
  const [newCauseText, setNewCauseText] = useState('');
  const [newCauseStatus, setNewCauseStatus] = useState('Requires Evidence');
  const [savedNotification, setSavedNotification] = useState(false);

  const categories = Object.keys(CATEGORY_META);

  const handleCreateCause = (category) => {
    if (!newCauseText.trim()) return;

    if (onAddCause) {
      onAddCause(category, newCauseText.trim(), newCauseStatus);
    }

    setNewCauseText('');
    setActiveAddCategory(null);
  };

  const handleSave = async () => {
    if (onSaveAll) {
      await onSaveAll();
    }
    setSavedNotification(true);
    setTimeout(() => setSavedNotification(false), 3000);
  };

  return (
    <div className="space-y-6">
      {/* Causal Classification Guide */}
      <div className="p-4 rounded-xl bg-white border border-[#E2E8F0] shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
        <div>
          <span className="font-bold text-[#142B45] block">
            Ishikawa 6M Causal Framework (Hypotheses Repository)
          </span>
          <span className="text-[#64748B]">
            All entries are classified as investigative hypotheses until backed by empirical proof.
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge variant="teal" size="sm">AI Suggestion</StatusBadge>
          <StatusBadge variant="warning" size="sm">Requires Evidence</StatusBadge>
          <StatusBadge variant="info" size="sm">Pending Review</StatusBadge>
          <StatusBadge variant="success" size="sm">Confirmed Cause</StatusBadge>
        </div>
      </div>

      {/* Action Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 bg-white rounded-xl border border-[#E2E8F0] shadow-2xs">
        <div>
          <h3 className="text-sm font-bold text-[#142B45]">
            6M Multi-Factor Causal Analysis Matrix
          </h3>
          <p className="text-xs text-[#64748B]">
            Evaluate root cause candidates across Manpower, Machine, Method, Material, Measurement, and Environment.
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
              {isGenerating ? 'Running AI 6M Reasoning...' : 'Generate AI Fishbone'}
            </Button>
          )}

          {onSaveAll && (
            <Button
              variant="primary"
              size="sm"
              leftIcon={Save}
              onClick={handleSave}
              disabled={isSaving || isGenerating}
            >
              {isSaving ? 'Persisting to DB...' : 'Save Fishbone'}
            </Button>
          )}
        </div>
      </div>

      {/* 6M Grid Layout */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {categories.map((catKey) => {
          const meta = CATEGORY_META[catKey];
          const Icon = meta.icon;
          const causesList = fishbone[catKey] || [];

          return (
            <Card key={catKey} className="flex flex-col h-full">
              <CardHeader className="py-3 bg-[#F8FAFC]">
                <div className="flex items-center space-x-2.5">
                  <div
                    className={`w-8 h-8 rounded-lg flex items-center justify-center ${meta.bg}`}
                  >
                    <Icon className={`w-4 h-4 ${meta.color}`} />
                  </div>
                  <div>
                    <CardTitle className="text-sm">{meta.label}</CardTitle>
                    <span className="text-[10px] text-[#64748B] block truncate max-w-[180px]">
                      {meta.description}
                    </span>
                  </div>
                </div>

                <span className="text-xs font-mono font-bold bg-white px-2 py-0.5 rounded border border-[#E2E8F0] text-[#142B45]">
                  {causesList.length}
                </span>
              </CardHeader>

              <CardContent className="flex-1 p-4 space-y-3">
                {causesList.length === 0 ? (
                  <div className="p-4 text-center rounded-lg border border-dashed border-[#CBD5E1] bg-[#FAFAFA]">
                    <p className="text-xs text-[#94A3B8]">
                      No potential failure modes logged under {catKey}.
                    </p>
                  </div>
                ) : (
                  <div className="space-y-2.5">
                    {causesList.map((causeItem) => {
                      const tagMeta = STATUS_TAGS[causeItem.status] || {
                        variant: 'neutral',
                        label: causeItem.status,
                      };

                      return (
                        <div
                          key={causeItem.id}
                          className="p-3 rounded-lg border border-[#E2E8F0] bg-white shadow-2xs space-y-2 group hover:border-[#CBD5E1] transition-all"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <p className="text-xs font-medium text-[#1E293B] leading-relaxed">
                              {causeItem.cause}
                            </p>
                            <button
                              type="button"
                              onClick={() => onRemoveCause && onRemoveCause(catKey, causeItem.id)}
                              className="text-[#94A3B8] hover:text-[#DC2626] p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity"
                              title="Delete hypothesis"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>

                          <div className="flex items-center justify-between pt-1 border-t border-[#F8FAFC]">
                            <StatusBadge variant={tagMeta.variant} size="sm">
                              {tagMeta.label}
                            </StatusBadge>

                            {/* Status update switcher */}
                            <select
                              value={causeItem.status}
                              onChange={(e) =>
                                onUpdateCauseStatus &&
                                onUpdateCauseStatus(catKey, causeItem.id, e.target.value)
                              }
                              className="text-[10px] bg-[#F8FAFC] border border-[#E2E8F0] rounded px-1.5 py-0.5 text-[#475569] focus:outline-none focus:border-[#0F9D91]"
                            >
                              <option value="AI Suggestion">AI Suggestion</option>
                              <option value="Requires Evidence">Requires Evidence</option>
                              <option value="Pending Review">Pending Review</option>
                              <option value="Evidence-Supported">Evidence-Supported</option>
                              <option value="Confirmed by Investigator">Confirmed Cause</option>
                            </select>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Inline Add Cause Trigger */}
                {activeAddCategory === catKey ? (
                  <div className="p-3 bg-[#F8FAFC] border border-[#CBD5E1] rounded-lg space-y-2 mt-2">
                    <label className="block text-[11px] font-semibold text-[#142B45]">
                      Add {catKey} Hypothesis:
                    </label>
                    <textarea
                      rows={2}
                      value={newCauseText}
                      onChange={(e) => setNewCauseText(e.target.value)}
                      placeholder={`e.g. Specific potential failure mode in ${catKey}...`}
                      className="block w-full text-xs p-2 rounded border border-[#CBD5E1] bg-white focus:outline-none focus:border-[#0F9D91]"
                      autoFocus
                    />

                    <div className="flex items-center justify-between pt-1">
                      <select
                        value={newCauseStatus}
                        onChange={(e) => setNewCauseStatus(e.target.value)}
                        className="text-[10px] bg-white border border-[#CBD5E1] rounded px-2 py-1 text-[#142B45]"
                      >
                        <option value="Requires Evidence">Requires Evidence</option>
                        <option value="AI Suggestion">AI Suggestion</option>
                        <option value="Pending Review">Pending Review</option>
                        <option value="Evidence-Supported">Evidence-Supported</option>
                      </select>

                      <div className="flex items-center space-x-1.5">
                        <Button
                          variant="ghost"
                          size="xs"
                          onClick={() => {
                            setActiveAddCategory(null);
                            setNewCauseText('');
                          }}
                        >
                          Cancel
                        </Button>
                        <Button
                          variant="accent"
                          size="xs"
                          onClick={() => handleCreateCause(catKey)}
                          disabled={!newCauseText.trim()}
                        >
                          Add
                        </Button>
                      </div>
                    </div>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => {
                      setActiveAddCategory(catKey);
                      setNewCauseText('');
                    }}
                    className="w-full py-2 border border-dashed border-[#CBD5E1] rounded-lg text-xs font-medium text-[#64748B] hover:text-[#0F9D91] hover:border-[#0F9D91] hover:bg-[#E6F7F5]/30 transition-all flex items-center justify-center space-x-1 cursor-pointer"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Add {catKey} Cause</span>
                  </button>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Save Action Footer */}
      {onSaveAll && (
        <div className="flex items-center justify-between p-4 bg-white rounded-xl border border-[#E2E8F0] shadow-2xs">
          <div className="text-xs text-[#64748B]">
            {savedNotification ? (
              <span className="text-[#059669] font-semibold flex items-center">
                <CheckCircle2 className="w-4 h-4 mr-1" /> Fishbone Causal Hypotheses Persisted in Database
              </span>
            ) : (
              <span>Persisting records associates 6M hypotheses with investigation {fishbone ? 'study' : ''} in PostgreSQL.</span>
            )}
          </div>

          <Button
            variant="primary"
            size="sm"
            leftIcon={Save}
            onClick={handleSave}
            disabled={isSaving || isGenerating}
          >
            {isSaving ? 'Persisting to DB...' : 'Save Fishbone Matrix'}
          </Button>
        </div>
      )}
    </div>
  );
}
