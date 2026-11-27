import React, { useRef, useState } from 'react';
import { SelectedFileItem } from '../../types/batch';
import { DOCUMENT_TYPES, EXPORTER_DOCUMENT_SLOTS } from '../../constants/documentTypes';
import {
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertTriangle,
  Trash2,
  ShieldCheck,
  Loader2,
  Upload,
  RefreshCw,
} from 'lucide-react';

interface UploadDocumentsSectionProps {
  selectedFiles: SelectedFileItem[];
  onAddFiles: (files: File[], explicitType?: string) => void;
  onRemoveFile: (id: string) => void;
  onChangeType: (id: string, newType: string) => void;
  onClearAll: () => void;
  onRunComplianceCheck: () => void;
  isRunning: boolean;
  uploadProgress: number;
  progressLabel: string;
  errorMessage: string | null;
  warningMessage: string | null;
  maxFiles?: number;
  showSectionHeader?: boolean;
}

export const UploadDocumentsSection: React.FC<UploadDocumentsSectionProps> = ({
  selectedFiles,
  onAddFiles,
  onRemoveFile,
  onChangeType,
  onClearAll,
  onRunComplianceCheck,
  isRunning,
  uploadProgress,
  progressLabel,
  errorMessage,
  warningMessage,
  maxFiles = 5,
  showSectionHeader = true,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const multiInputRef = useRef<HTMLInputElement>(null);
  const slotInputRefs = useRef<Record<string, HTMLInputElement | null>>({});

  const hasInvalidFiles = selectedFiles.some((f) => !!f.validationError);
  const validCount = selectedFiles.filter((f) => !f.validationError).length;

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (isRunning) return;
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      onAddFiles(Array.from(e.dataTransfer.files));
    }
  };

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
      {/* Hidden Multi-File Input */}
      <input
        ref={multiInputRef}
        type="file"
        accept=".pdf,application/pdf"
        multiple
        style={{ display: 'none' }}
        disabled={isRunning}
        onChange={(e) => {
          if (e.target.files && e.target.files.length > 0) {
            onAddFiles(Array.from(e.target.files));
            e.target.value = '';
          }
        }}
      />

      {/* Primary Verification Dropzone Card */}
      <div
        style={{
          backgroundColor: '#FFFFFF',
          border: '1px solid #C5D7E8',
          borderRadius: '16px',
          padding: '22px 24px 24px',
          boxShadow: '0 10px 28px rgba(16, 42, 67, 0.08)',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            height: '4px',
            background: 'linear-gradient(90deg, #102A43 0%, #1E3A5F 45%, #456B8B 80%, #9FBAD0 100%)',
          }}
        />

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '12px',
            marginBottom: '16px',
          }}
        >
          {showSectionHeader ? (
            <div>
              <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 700, color: '#102A43' }}>
                Section 1: Upload Export Customs Documents
              </h3>
              <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#456B8B' }}>
                Upload up to {maxFiles} digital or scanned PDF documents for AI extraction and verification.
              </p>
            </div>
          ) : (
            <div>
              <h2 style={{ margin: 0, fontSize: '17px', fontWeight: 700, color: '#102A43' }}>
                Drag &amp; Drop PDF Batch Area
              </h2>
              <p style={{ margin: '3px 0 0 0', fontSize: '13px', color: '#456B8B' }}>
                Drop multiple export PDFs here for auto-detection, or upload into a specific document card below.
              </p>
            </div>
          )}

          {selectedFiles.length > 0 && (
            <button
              type="button"
              onClick={onClearAll}
              disabled={isRunning}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 12px',
                fontSize: '12px',
                fontWeight: 600,
                backgroundColor: '#EAF2F8',
                color: '#102A43',
                border: '1px solid #9FBAD0',
                borderRadius: '7px',
                cursor: isRunning ? 'not-allowed' : 'pointer',
              }}
            >
              <Trash2 size={13} /> Clear Queue ({selectedFiles.length}/{maxFiles})
            </button>
          )}
        </div>

        {/* Main Drag & Drop Target */}
        <div
          className={`ecc-upload-dropzone ${isDragging ? 'dragging' : ''}`}
          onDragOver={(e) => {
            e.preventDefault();
            if (!isRunning) setIsDragging(true);
          }}
          onDragLeave={(e) => {
            e.preventDefault();
            setIsDragging(false);
          }}
          onDrop={handleDrop}
          onClick={() => !isRunning && multiInputRef.current?.click()}
          style={{
            cursor: isRunning ? 'not-allowed' : 'pointer',
            marginBottom: '18px',
          }}
        >
          <div
            style={{
              width: '54px',
              height: '54px',
              borderRadius: '14px',
              background: 'linear-gradient(135deg, #102A43 0%, #1E3A5F 100%)',
              color: '#FFFFFF',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '12px',
              boxShadow: '0 8px 20px rgba(16, 42, 67, 0.22)',
            }}
          >
            <UploadCloud size={26} />
          </div>

          <div style={{ fontSize: '16px', fontWeight: 700, color: '#102A43' }}>
            Drag and drop up to {maxFiles} export PDF files here
          </div>
          <div style={{ fontSize: '13px', color: '#456B8B', marginTop: '5px', marginBottom: '16px' }}>
            Supported format: <strong>PDF (.pdf)</strong> • Digital &amp; scanned PDFs • Maximum <strong>25 MB</strong> per file
          </div>

          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap', justifyContent: 'center' }}>
            <button
              type="button"
              id="upload-browse-files-btn"
              onClick={(e) => {
                e.stopPropagation();
                if (!isRunning) {
                  multiInputRef.current?.click();
                }
              }}
              disabled={isRunning}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '7px',
                padding: '9px 20px',
                fontSize: '13.5px',
                fontWeight: 700,
                background: 'linear-gradient(135deg, #102A43 0%, #1E3A5F 100%)',
                color: '#FFFFFF',
                border: 'none',
                borderRadius: '8px',
                cursor: isRunning ? 'not-allowed' : 'pointer',
                boxShadow: '0 4px 12px rgba(16, 42, 67, 0.18)',
              }}
            >
              <Upload size={14} />
              <span>Browse Files</span>
            </button>

            <span
              style={{
                fontSize: '12px',
                fontWeight: 600,
                color: validCount > 0 ? '#0D9488' : '#456B8B',
                backgroundColor: validCount > 0 ? '#E6F4F1' : '#EAF2F8',
                border: `1px solid ${validCount > 0 ? '#99D5CE' : '#C5D7E8'}`,
                padding: '7px 12px',
                borderRadius: '8px',
              }}
            >
              {validCount === 0
                ? 'No files selected yet'
                : `${validCount} of ${maxFiles} PDF file(s) staged`}
            </span>
          </div>
        </div>

        {/* Inline Action Bar (Always visible so Start Compliance Verification is clear & prominent) */}
        <div
          style={{
            padding: '14px 16px',
            borderRadius: '10px',
            backgroundColor: '#EAF2F8',
            border: '1px solid #C5D7E8',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '12px',
          }}
        >
          <div style={{ fontSize: '13px', color: '#1E3A5F', fontWeight: 500 }}>
            {selectedFiles.length === 0
              ? 'Attach 1 to 5 trade PDFs above or inside the document cards below to begin verification.'
              : `${selectedFiles.length} file(s) queued — ready for OCR, Gemini AI extraction, LangGraph & DGFT/CBIC checks.`}
          </div>

          <button
            type="button"
            id="run-compliance-check-btn"
            className="ecc-btn-verify"
            onClick={onRunComplianceCheck}
            disabled={isRunning || hasInvalidFiles || selectedFiles.length === 0}
          >
            {isRunning ? (
              <>
                <Loader2 size={16} />
                <span>Verifying Documents...</span>
              </>
            ) : (
              <>
                <ShieldCheck size={17} />
                <span>Start Compliance Verification</span>
              </>
            )}
          </button>
        </div>

        {isRunning && (
          <div style={{ marginTop: '14px' }}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                fontSize: '12.5px',
                fontWeight: 600,
                color: '#1E3A5F',
                marginBottom: '6px',
              }}
            >
              <span>{progressLabel}</span>
              <span>{uploadProgress}%</span>
            </div>
            <div style={{ height: '9px', backgroundColor: '#EAF2F8', borderRadius: '999px', overflow: 'hidden', border: '1px solid #C5D7E8' }}>
              <div
                style={{
                  height: '100%',
                  width: `${uploadProgress}%`,
                  background: 'linear-gradient(90deg, #1E3A5F 0%, #456B8B 50%, #0D9488 100%)',
                  transition: 'width 0.3s ease',
                }}
              />
            </div>
          </div>
        )}

        {/* Alerts */}
        {warningMessage && (
          <div
            style={{
              marginTop: '14px',
              padding: '10px 14px',
              backgroundColor: 'var(--status-partial-bg)',
              border: '1px solid var(--status-partial-border)',
              borderRadius: '8px',
              color: 'var(--status-partial-text)',
              fontSize: '13px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <AlertTriangle size={16} /> <span>{warningMessage}</span>
          </div>
        )}

        {errorMessage && (
          <div
            style={{
              marginTop: '14px',
              padding: '10px 14px',
              backgroundColor: 'var(--status-error-bg)',
              border: '1px solid var(--status-error-border)',
              borderRadius: '8px',
              color: 'var(--status-error-text)',
              fontSize: '13px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <AlertTriangle size={16} /> <span>{errorMessage}</span>
          </div>
        )}
      </div>

      {/* 5 Individual Document Type Cards */}
      <div
        style={{
          backgroundColor: '#FFFFFF',
          border: '1px solid #C5D7E8',
          borderRadius: '16px',
          padding: '20px 24px',
          boxShadow: '0 8px 22px rgba(16, 42, 67, 0.06)',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '8px',
            marginBottom: '14px',
          }}
        >
          <div>
            <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 700, color: '#102A43' }}>
              Required Export Trade Documents (5 Document Types)
            </h3>
            <p style={{ margin: '2px 0 0 0', fontSize: '12.5px', color: '#456B8B' }}>
              Attach PDFs to individual document cards or let the batch uploader classify them automatically.
            </p>
          </div>
          <span
            style={{
              fontSize: '12px',
              fontWeight: 700,
              color: '#102A43',
              backgroundColor: '#EAF2F8',
              padding: '4px 10px',
              borderRadius: '999px',
              border: '1px solid #9FBAD0',
            }}
          >
            {EXPORTER_DOCUMENT_SLOTS.filter((s) =>
              selectedFiles.some((f) => f.documentType === s.type && !f.validationError)
            ).length}{' '}
            / 5 Slots Assigned
          </span>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(215px, 1fr))',
            gap: '12px',
          }}
        >
          {EXPORTER_DOCUMENT_SLOTS.map((slot) => {
            const matchedItem = selectedFiles.find((f) => f.documentType === slot.type);
            const hasSlotErr = !!matchedItem?.validationError;

            return (
              <div
                key={slot.type}
                className="ecc-doc-slot-card"
                style={{
                  border: `1px solid ${
                    hasSlotErr ? '#FECACA' : matchedItem ? '#0D9488' : '#C5D7E8'
                  }`,
                  backgroundColor: hasSlotErr
                    ? '#FEF2F2'
                    : matchedItem
                    ? '#F2FAF8'
                    : '#F8FBFE',
                }}
              >
                <input
                  type="file"
                  accept=".pdf,application/pdf"
                  style={{ display: 'none' }}
                  ref={(el) => {
                    slotInputRefs.current[slot.type] = el;
                  }}
                  disabled={isRunning}
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      onAddFiles([e.target.files[0]], slot.type);
                      e.target.value = '';
                    }
                  }}
                />

                <div>
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      gap: '6px',
                      marginBottom: '8px',
                    }}
                  >
                    <span
                      style={{
                        fontSize: '10.5px',
                        fontWeight: 800,
                        padding: '2px 7px',
                        borderRadius: '5px',
                        backgroundColor: '#102A43',
                        color: '#FFFFFF',
                        letterSpacing: '0.04em',
                      }}
                    >
                      {slot.shortCode}
                    </span>

                    {matchedItem ? (
                      <span
                        style={{
                          fontSize: '11px',
                          fontWeight: 700,
                          padding: '2px 8px',
                          borderRadius: '999px',
                          backgroundColor: hasSlotErr ? '#FEE2E2' : '#E6F4F1',
                          color: hasSlotErr ? '#991B1B' : '#0D9488',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                        }}
                      >
                        <CheckCircle2 size={11} />
                        {hasSlotErr ? 'Invalid' : 'Attached'}
                      </span>
                    ) : (
                      <span
                        style={{
                          fontSize: '11px',
                          fontWeight: 600,
                          padding: '2px 8px',
                          borderRadius: '999px',
                          backgroundColor: '#EAF2F8',
                          color: '#456B8B',
                        }}
                      >
                        Pending
                      </span>
                    )}
                  </div>

                  <div style={{ fontSize: '14px', fontWeight: 700, color: '#102A43', marginBottom: '4px' }}>
                    {slot.type}
                  </div>

                  <div style={{ fontSize: '11.5px', color: '#456B8B', lineHeight: 1.45 }}>
                    {matchedItem ? (
                      <span style={{ fontWeight: 600, color: '#102A43', wordBreak: 'break-word' }}>
                        {matchedItem.file.name} ({matchedItem.sizeFormatted})
                      </span>
                    ) : (
                      slot.description
                    )}
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '6px', marginTop: '4px' }}>
                  <button
                    type="button"
                    onClick={() => slotInputRefs.current[slot.type]?.click()}
                    disabled={isRunning || (!matchedItem && selectedFiles.length >= maxFiles)}
                    style={{
                      flex: 1,
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '5px',
                      padding: '6px 10px',
                      fontSize: '11.5px',
                      fontWeight: 600,
                      backgroundColor: matchedItem ? '#FFFFFF' : '#1E3A5F',
                      color: matchedItem ? '#102A43' : '#FFFFFF',
                      border: `1px solid ${matchedItem ? '#9FBAD0' : '#1E3A5F'}`,
                      borderRadius: '6px',
                      cursor:
                        isRunning || (!matchedItem && selectedFiles.length >= maxFiles)
                          ? 'not-allowed'
                          : 'pointer',
                      opacity: isRunning || (!matchedItem && selectedFiles.length >= maxFiles) ? 0.55 : 1,
                    }}
                  >
                    {matchedItem ? <RefreshCw size={11} /> : <Upload size={11} />}
                    <span>{matchedItem ? 'Replace' : 'Select PDF'}</span>
                  </button>

                  {matchedItem && (
                    <button
                      type="button"
                      onClick={() => onRemoveFile(matchedItem.id)}
                      disabled={isRunning}
                      title={`Remove ${slot.type}`}
                      style={{
                        padding: '6px 8px',
                        borderRadius: '6px',
                        border: '1px solid #9FBAD0',
                        backgroundColor: '#FFFFFF',
                        color: '#102A43',
                        cursor: isRunning ? 'not-allowed' : 'pointer',
                      }}
                    >
                      <Trash2 size={12} />
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Staged Files Queue Details */}
      {selectedFiles.length > 0 && (
        <div
          style={{
            backgroundColor: '#FFFFFF',
            border: '1px solid #C5D7E8',
            borderRadius: '16px',
            padding: '18px 24px',
            boxShadow: '0 8px 22px rgba(16, 42, 67, 0.06)',
          }}
        >
          <h4 style={{ margin: '0 0 12px 0', fontSize: '15px', fontWeight: 700, color: '#102A43' }}>
            Uploaded File Queue ({selectedFiles.length} / {maxFiles})
          </h4>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {selectedFiles.map((item, idx) => {
              const err = !!item.validationError;
              return (
                <div
                  key={item.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    flexWrap: 'wrap',
                    gap: '10px',
                    padding: '10px 14px',
                    borderRadius: '9px',
                    backgroundColor: err ? '#FEF2F2' : '#EAF2F8',
                    border: `1px solid ${err ? '#FECACA' : '#C5D7E8'}`,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: '220px', flex: 1 }}>
                    <FileText size={18} color={err ? '#991B1B' : '#102A43'} />
                    <div>
                      <div style={{ fontSize: '13px', fontWeight: 600, color: '#102A43' }}>
                        #{idx + 1} {item.file.name}
                      </div>
                      <div style={{ fontSize: '11.5px', color: err ? '#991B1B' : '#456B8B' }}>
                        {item.sizeFormatted} •{' '}
                        <span style={{ color: err ? '#991B1B' : '#0D9488', fontWeight: 600 }}>
                          {item.validationError || 'Ready for verification'}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <select
                      value={item.documentType}
                      onChange={(e) => onChangeType(item.id, e.target.value)}
                      disabled={isRunning || err}
                      style={{
                        padding: '6px 10px',
                        fontSize: '12px',
                        borderRadius: '6px',
                        border: '1px solid #9FBAD0',
                        backgroundColor: '#FFFFFF',
                        color: '#102A43',
                        fontWeight: 500,
                      }}
                    >
                      <option value="Auto-Detect">Auto-Detect Document Type</option>
                      {DOCUMENT_TYPES.map((t) => (
                        <option key={t} value={t}>
                          {t}
                        </option>
                      ))}
                    </select>

                    <button
                      type="button"
                      onClick={() => onRemoveFile(item.id)}
                      disabled={isRunning}
                      title="Remove file"
                      style={{
                        padding: '6px 8px',
                        borderRadius: '6px',
                        border: '1px solid #9FBAD0',
                        backgroundColor: '#FFFFFF',
                        color: '#102A43',
                        cursor: isRunning ? 'not-allowed' : 'pointer',
                      }}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
