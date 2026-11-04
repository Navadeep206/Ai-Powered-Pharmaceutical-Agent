import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '../common/Card';
import Input from '../common/Input';
import Select from '../common/Select';
import Button from '../common/Button';
import { PlusCircle, X } from 'lucide-react';

/**
 * Form to register new evidence artifacts or investigator inquiry questions.
 */
export default function EvidenceForm({ onAddEvidence, onCancel }) {
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState('Supporting Evidence');
  const [type, setType] = useState('SCADA Sensor Data');
  const [reference, setReference] = useState('');
  const [notes, setNotes] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!title.trim()) return;

    onAddEvidence({
      title: title.trim(),
      category,
      type,
      reference: reference.trim() || 'Pending Ref ID',
      notes: notes.trim(),
      status: category === 'Missing Evidence' ? 'Pending Collection' : 'Under Review',
    });

    setTitle('');
    setReference('');
    setNotes('');
  };

  return (
    <Card className="border-[#0F9D91]/40 shadow-md">
      <CardHeader className="bg-[#E6F7F5]/50 py-3">
        <div className="flex items-center justify-between w-full">
          <CardTitle className="text-sm font-bold text-[#142B45]">
            Link New Evidence or Inquiry
          </CardTitle>
          <button
            type="button"
            onClick={onCancel}
            className="text-[#64748B] hover:text-[#142B45] p-1 rounded-md"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </CardHeader>

      <form onSubmit={handleSubmit}>
        <CardContent className="p-4 space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Select
              label="Evidence Category"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              options={[
                { value: 'Supporting Evidence', label: 'Supporting Evidence (Confirms hypothesis)' },
                { value: 'Contradictory Evidence', label: 'Contradictory Evidence (Refutes hypothesis)' },
                { value: 'Missing Evidence', label: 'Missing Evidence (Data gap to collect)' },
                { value: 'Investigator Questions', label: 'Investigator Inquiry (Safety/Process query)' },
              ]}
              required
            />

            <Select
              label="Evidence Type / Format"
              value={type}
              onChange={(e) => setType(e.target.value)}
              options={[
                { value: 'SCADA Sensor Data', label: 'SCADA Sensor Data (Time-series / Historian)' },
                { value: 'HPLC Chromatogram', label: 'HPLC / GC Chromatogram (Analytical Lab)' },
                { value: 'Batch Manufacturing Record', label: 'Batch Manufacturing Record (BMR)' },
                { value: 'CoA / Vendor Spec', label: 'CoA / Raw Material Specification' },
                { value: 'Calibration Certificate', label: 'Calibration Certificate / PM Log' },
                { value: 'Investigator Inquiry', label: 'Investigator Inquiry / Engineering Note' },
              ]}
              required
            />
          </div>

          <Input
            label="Evidence Summary / Question Title"
            placeholder="e.g. Chiller secondary flow transmitter FT-102B calibration record"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Input
              label="Document / Telemetry Reference"
              placeholder="e.g. CAL-2026-FT102B.pdf, SCADA Tag TIC-102A"
              value={reference}
              onChange={(e) => setReference(e.target.value)}
              helperText="Physical binder reference, file name, or database tag"
            />

            <div>
              <label className="block text-xs font-semibold text-[#142B45] mb-1.5 uppercase tracking-wider">
                Investigator Notes / Observations
              </label>
              <textarea
                rows={2}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Key finding or corroborating data points..."
                className="block w-full rounded-lg border border-[#CBD5E1] text-xs p-2.5 bg-white focus:outline-none focus:border-[#0F9D91]"
              />
            </div>
          </div>
        </CardContent>

        <CardFooter className="py-2.5 bg-[#F8FAFC]">
          <span className="text-xs text-[#64748B]">
            Evidence items logged contemporaneously per 21 CFR Part 11
          </span>
          <div className="flex items-center space-x-2">
            <Button variant="ghost" size="xs" onClick={onCancel}>
              Cancel
            </Button>
            <Button
              type="submit"
              variant="accent"
              size="xs"
              leftIcon={PlusCircle}
              disabled={!title.trim()}
            >
              Link Evidence
            </Button>
          </div>
        </CardFooter>
      </form>
    </Card>
  );
}

