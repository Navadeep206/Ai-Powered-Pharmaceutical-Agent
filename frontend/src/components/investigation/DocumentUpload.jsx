import React, { useRef, useState } from 'react';
import { UploadCloud, FileText, X, RefreshCw, AlertCircle, CheckCircle, AlertTriangle } from 'lucide-react';
import Button from '../common/Button';

/**
 * PDF Document Upload drop zone with client-side format & size validation.
 * Accepts PDF files for backend parsing and OCR verification.
 */
export default function DocumentUpload({
  fileInfo,
  onFileSelect,
  onFileRemove,
  error,
  setError,
  ocrWarning,
}) {
  const fileInputRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);

  const formatFileSize = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    validateAndSetFile(file);
  };

  const validateAndSetFile = (file) => {
    if (!file) return;

    // Validate PDF MIME type and extension
    const isPdf =
      file.type === 'application/pdf' ||
      file.name.toLowerCase().endsWith('.pdf');

    if (!isPdf) {
      setError('Invalid file format. Only PDF documents (e.g., BMR, SOP, SCADA reports) are supported.');
      return;
    }

    // Size limit check (25 MB)
    if (file.size > 25 * 1024 * 1024) {
      setError('File size exceeds the 25 MB limit for document upload.');
      return;
    }

    setError(null);
    const meta = {
      name: file.name,
      size: formatFileSize(file.size),
      rawBytes: file.size,
      type: file.type || 'application/pdf',
      lastModified: new Date(file.lastModified).toLocaleDateString(),
    };

    onFileSelect(meta, file);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    validateAndSetFile(file);
  };

  return (
    <div className="space-y-4">
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,application/pdf"
        className="hidden"
        onChange={handleFileChange}
      />

      {fileInfo ? (
        /* Selected File Card */
        <div className="bg-white p-5 rounded-xl border border-[#CBD5E1] shadow-2xs space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-lg bg-[#E6F7F5] text-[#0F9D91] flex items-center justify-center shrink-0">
                <FileText className="w-5 h-5" />
              </div>
              <div>
                <p className="text-sm font-semibold text-[#142B45] truncate max-w-md">
                  {fileInfo.name}
                </p>
                <p className="text-xs text-[#64748B]">
                  PDF Document &bull; {fileInfo.size} &bull; Modified {fileInfo.lastModified}
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <Button
                variant="secondary"
                size="xs"
                leftIcon={RefreshCw}
                onClick={() => fileInputRef.current?.click()}
              >
                Replace
              </Button>
              <button
                type="button"
                onClick={onFileRemove}
                className="p-1.5 text-[#64748B] hover:text-[#DC2626] hover:bg-[#FEF2F2] rounded-lg transition"
                title="Remove file"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          <div className="p-2.5 rounded-lg bg-[#ECFDF5] border border-[#A7F3D0] flex items-center space-x-2 text-xs text-[#065F46]">
            <CheckCircle className="w-4 h-4 text-[#059669] shrink-0" />
            <span>PDF validated locally. Ready for secure text parsing and AI structured extraction.</span>
          </div>

          {ocrWarning && (
            <div className="p-2.5 rounded-lg bg-[#FFFBEB] border border-[#FDE68A] flex items-center space-x-2 text-xs text-[#92400E]">
              <AlertTriangle className="w-4 h-4 text-[#D97706] shrink-0" />
              <span>{ocrWarning}</span>
            </div>
          )}
        </div>
      ) : (
        /* Empty Upload Drop Area */
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-200 ${
            isDragging
              ? 'border-[#0F9D91] bg-[#E6F7F5]/40 scale-[1.005]'
              : 'border-[#CBD5E1] bg-[#F8FAFC] hover:bg-white hover:border-[#0F9D91]'
          }`}
        >
          <div className="w-12 h-12 rounded-full bg-white border border-[#E2E8F0] shadow-2xs mx-auto flex items-center justify-center text-[#0F9D91] mb-3">
            <UploadCloud className="w-6 h-6" />
          </div>

          <h4 className="text-sm font-semibold text-[#142B45]">
            Choose a PDF document or drag and drop here
          </h4>
          <p className="text-xs text-[#64748B] mt-1 max-w-sm mx-auto">
            Upload electronic Batch Manufacturing Records (BMR), SCADA trend reports, or QA deviation logs.
          </p>

          <div className="mt-4 inline-flex items-center text-xs font-semibold text-[#0F9D91] bg-[#E6F7F5] px-3 py-1.5 rounded-md">
            Only .PDF files accepted (Max 25 MB)
          </div>
        </div>
      )}

      {error && (
        <div className="p-3 bg-[#FEF2F2] border border-[#FECACA] rounded-lg text-xs text-[#991B1B] flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-[#DC2626]" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}
