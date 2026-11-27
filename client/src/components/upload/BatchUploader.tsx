import React, { useState, useRef, useCallback } from 'react';
import { SelectedFileItem, BatchUploadResponse } from '../../types/batch';
import { batchService, BatchUploadError } from '../../services/batchService';
import { DocumentQueueItem } from './DocumentQueueItem';
import {
  UploadCloud,
  AlertTriangle,
  Loader2,
  Trash2,
  PlusCircle,
  ShieldCheck,
  HelpCircle,
  FilePlus2,
} from 'lucide-react';

interface BatchUploaderProps {
  onBatchComplete: (response: BatchUploadResponse) => void;
  maxFiles?: number;
  maxFileSizeMb?: number;
}

const MAX_FILES_DEFAULT = 5;
const MAX_FILE_SIZE_MB_DEFAULT = 25;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB_DEFAULT * 1024 * 1024;

function buildSamplePdfFile(filename: string, title: string, lines: string[]): File {
  const esc = (s: string) => s.replace(/\\/g, '\\\\').replace(/\(/g, '\\(').replace(/\)/g, '\\)');
  const textOps = [title, '', ...lines]
    .map((line, idx) => `BT /F1 11 Tf 50 ${750 - idx * 18} Td (${esc(line)}) Tj ET`)
    .join('\n');
  const objs = [
    '1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n',
    '2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n',
    '3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n',
    `4 0 obj\n<< /Length ${textOps.length} >>\nstream\n${textOps}\nendstream\nendobj\n`,
    '5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n',
  ];
  let pdf = '%PDF-1.4\n';
  const offsets: number[] = [];
  for (const obj of objs) {
    offsets.push(pdf.length);
    pdf += obj;
  }
  const xrefOffset = pdf.length;
  pdf += `xref\n0 ${objs.length + 1}\n0000000000 65535 f \n`;
  for (const off of offsets) {
    pdf += `${String(off).padStart(10, '0')} 00000 n \n`;
  }
  pdf += `trailer\n<< /Size ${objs.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF\n`;
  return new File([pdf], filename, { type: 'application/pdf' });
}

export const BatchUploader: React.FC<BatchUploaderProps> = ({
  onBatchComplete,
  maxFiles = MAX_FILES_DEFAULT,
  maxFileSizeMb = MAX_FILE_SIZE_MB_DEFAULT,
}) => {
  const [selectedFiles, setSelectedFiles] = useState<SelectedFileItem[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [progressStage, setProgressStage] = useState<string>(
    'Processing OCR, Gemini Intelligence & Compliance Audit...'
  );
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [generalWarning, setGeneralWarning] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const processIncomingFiles = useCallback(
    (filesToAdd: File[]) => {
      setGeneralError(null);
      setGeneralWarning(null);

      if (!filesToAdd || filesToAdd.length === 0) return;

      const currentCount = selectedFiles.length;
      let availableSlots = maxFiles - currentCount;

      if (availableSlots <= 0) {
        setGeneralWarning(
          `Batch limit of ${maxFiles} documents reached. Remove a file before adding more.`
        );
        return;
      }

      const filesToProcess = filesToAdd.slice(0, availableSlots);
      if (filesToAdd.length > availableSlots) {
        setGeneralWarning(
          `Maximum ${maxFiles} files allowed. Only first ${availableSlots} files were added.`
        );
      }

      const newItems: SelectedFileItem[] = [];

      for (const file of filesToProcess) {
        let validationError: string | null = null;

        // Check format
        const isPdfExt = file.name.toLowerCase().endsWith('.pdf');

        if (!isPdfExt) {
          validationError = 'Invalid file format: Only .pdf files are permitted.';
        } else if (file.size > MAX_FILE_SIZE_BYTES) {
          validationError = `File exceeds ${maxFileSizeMb} MB limit (${formatFileSize(file.size)}).`;
        } else if (file.size === 0) {
          validationError = 'File is empty (0 bytes).';
        }

        // Check for duplicate names in current queue
        const isDuplicateName = selectedFiles.some(
          (existing) => existing.file.name.toLowerCase() === file.name.toLowerCase()
        );
        if (isDuplicateName) {
          setGeneralWarning(
            `Notice: '${file.name}' is already in the queue. Duplicate content will be skipped.`
          );
        }

        newItems.push({
          id: `file_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`,
          file,
          documentType: 'Auto-Detect',
          sizeFormatted: formatFileSize(file.size),
          sizeBytes: file.size,
          validationError,
        });
      }

      setSelectedFiles((prev) => [...prev, ...newItems]);
    },
    [selectedFiles, maxFiles, maxFileSizeMb]
  );

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isUploading) {
      setIsDragging(true);
    }
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (isUploading) return;

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFiles = Array.from(e.dataTransfer.files);
      processIncomingFiles(droppedFiles);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const chosenFiles = Array.from(e.target.files);
      processIncomingFiles(chosenFiles);
      // Reset input value so re-selecting same file triggers onChange
      e.target.value = '';
    }
  };

  const handleRemove = (id: string) => {
    setSelectedFiles((prev) => prev.filter((item) => item.id !== id));
    setGeneralError(null);
    setGeneralWarning(null);
  };

  const handleTypeChange = (id: string, newType: string) => {
    setSelectedFiles((prev) =>
      prev.map((item) => (item.id === id ? { ...item, documentType: newType } : item))
    );
  };

  const handleReplaceFile = (id: string, newFile: File) => {
    let validationError: string | null = null;
    const isPdfExt = newFile.name.toLowerCase().endsWith('.pdf');

    if (!isPdfExt) {
      validationError = 'Invalid file format: Only .pdf files are permitted.';
    } else if (newFile.size > MAX_FILE_SIZE_BYTES) {
      validationError = `File exceeds ${maxFileSizeMb} MB limit (${formatFileSize(newFile.size)}).`;
    } else if (newFile.size === 0) {
      validationError = 'File is empty (0 bytes).';
    }

    setSelectedFiles((prev) =>
      prev.map((item) =>
        item.id === id
          ? {
              ...item,
              file: newFile,
              sizeFormatted: formatFileSize(newFile.size),
              sizeBytes: newFile.size,
              validationError,
            }
          : item
      )
    );
  };

  const handleClearAll = () => {
    setSelectedFiles([]);
    setGeneralError(null);
    setGeneralWarning(null);
  };

  const handleLoadSampleBatch = () => {
    if (isUploading) return;
    setGeneralError(null);
    setGeneralWarning(null);

    const sampleDocs: Array<{ file: File; type: string }> = [
      {
        type: 'Commercial Invoice',
        file: buildSamplePdfFile('sample_commercial_invoice.pdf', 'COMMERCIAL INVOICE', [
          'Invoice No: INV-2024-001',
          'Exporter: Global Exports Ltd | IEC: 0312345678 | GSTIN: 27AAACG0000A1ZS',
          'Consignee: Acme Trading GmbH, Germany',
          'Currency: EUR | Total Amount: 22500.00 | Incoterms: FOB',
          'HS Code: 848340 | Qty: 500 PCS',
        ]),
      },
      {
        type: 'Packing List',
        file: buildSamplePdfFile('sample_packing_list.pdf', 'PACKING LIST', [
          'Packing List No: PL-2024-001 | Invoice Ref: INV-2024-001',
          'Total Packages: 10 | Gross Weight: 1250 KG | Net Weight: 1100 KG',
        ]),
      },
      {
        type: 'Purchase Order',
        file: buildSamplePdfFile('sample_purchase_order.pdf', 'PURCHASE ORDER', [
          'PO No: PO-998877 | Buyer: Acme Trading GmbH',
          'Vendor: Global Exports Ltd | Currency: EUR | Total: 22500.00',
        ]),
      },
      {
        type: 'Shipping Bill',
        file: buildSamplePdfFile('sample_shipping_bill.pdf', 'SHIPPING BILL', [
          'Shipping Bill No: SB-11223344 | Port: INMAA1',
          'Invoice Ref: INV-2024-001 | FOB Value: 22500.00 EUR',
        ]),
      },
      {
        type: 'Certificate of Origin',
        file: buildSamplePdfFile('sample_certificate_of_origin.pdf', 'CERTIFICATE OF ORIGIN', [
          'Certificate No: COO-556677 | Chamber: Bombay Chamber of Commerce',
          'Origin Criterion: Wholly Obtained (WO) | Invoice Ref: INV-2024-001',
        ]),
      },
    ];

    setSelectedFiles(
      sampleDocs.map((entry, idx) => ({
        id: `sample_${Date.now()}_${idx}`,
        file: entry.file,
        documentType: entry.type,
        sizeFormatted: formatFileSize(entry.file.size),
        sizeBytes: entry.file.size,
        validationError: null,
      }))
    );
  };

  const handleSubmitBatch = async () => {
    if (selectedFiles.length === 0) {
      setGeneralError('Please select at least 1 customs PDF document to upload.');
      return;
    }

    // Verify no files have validation errors
    const invalidItems = selectedFiles.filter((item) => !!item.validationError);
    if (invalidItems.length > 0) {
      setGeneralError(
        `Please remove or replace the ${invalidItems.length} invalid file(s) before uploading.`
      );
      return;
    }

    setIsUploading(true);
    setUploadProgress(5);
    setProgressStage('Uploading PDFs via multipart/form-data...');
    setGeneralError(null);
    setGeneralWarning(null);

    const filesToUpload = selectedFiles.map((item) => item.file);
    const documentTypesToUpload = selectedFiles.map((item) => item.documentType);

    // Advance smoothly during server-side OCR/AI processing after upload bytes finish
    const progressTimer = setInterval(() => {
      setUploadProgress((prev) => (prev >= 70 && prev < 94 ? prev + 4 : prev));
    }, 900);

    try {
      const response = await batchService.uploadBatch(
        filesToUpload,
        documentTypesToUpload,
        (pct, stageLabel) => {
          setUploadProgress((prev) => Math.max(prev, pct));
          if (stageLabel) setProgressStage(stageLabel);
        }
      );
      clearInterval(progressTimer);
      setUploadProgress(100);
      setProgressStage('Batch verification complete.');

      setTimeout(() => {
        setIsUploading(false);
        setUploadProgress(0);
        onBatchComplete(response);
      }, 300);
    } catch (err: any) {
      clearInterval(progressTimer);
      setIsUploading(false);
      setUploadProgress(0);

      if (err instanceof BatchUploadError) {
        setGeneralError(err.message);
      } else {
        setGeneralError(err.message || 'An unexpected error occurred during batch ingestion.');
      }
    }
  };

  const hasInvalidFilesInQueue = selectedFiles.some((f) => !!f.validationError);
  const totalSizeBytes = selectedFiles.reduce((acc, curr) => acc + curr.sizeBytes, 0);

  return (
    <div style={{ maxWidth: '900px', margin: '0 auto' }}>
      {/* Hidden file input */}
      <input
        type="file"
        ref={fileInputRef}
        accept=".pdf,application/pdf"
        multiple
        style={{ display: 'none' }}
        onChange={handleFileInputChange}
        disabled={isUploading}
      />

      {/* Drop Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !isUploading && fileInputRef.current?.click()}
        style={{
          border: `2px dashed ${isDragging ? 'var(--primary-blush)' : 'var(--border-blush)'}`,
          borderRadius: 'var(--radius-lg)',
          backgroundColor: isDragging ? 'var(--primary-blush-subtle)' : 'var(--bg-surface)',
          padding: '40px 24px',
          textAlign: 'center',
          cursor: isUploading ? 'not-allowed' : 'pointer',
          transition: 'all 0.25s ease',
          boxShadow: isDragging ? 'var(--shadow-md)' : 'var(--shadow-sm)',
          position: 'relative',
        }}
      >
        <div
          style={{
            width: '64px',
            height: '64px',
            borderRadius: '50%',
            backgroundColor: 'var(--primary-blush-light)',
            color: 'var(--primary-blush)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 16px auto',
          }}
        >
          <UploadCloud size={32} />
        </div>

        <h3 style={{ margin: '0 0 6px 0', fontSize: '18px', color: 'var(--text-main)', fontWeight: 600 }}>
          Drag & Drop Customs Documents Here
        </h3>
        <p style={{ margin: '0 0 16px 0', fontSize: '14px', color: 'var(--text-muted)' }}>
          or <span style={{ color: 'var(--primary-blush)', fontWeight: 600, textDecoration: 'underline' }}>browse your computer</span> to select up to 5 export PDFs
        </p>

        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '16px',
            fontSize: '12px',
            color: 'var(--text-subtle)',
            backgroundColor: 'var(--bg-subtle)',
            padding: '8px 16px',
            borderRadius: 'var(--radius-md)',
          }}
        >
          <span>✓ Accepted: PDF format</span>
          <span>•</span>
          <span>Max size: 25 MB per file</span>
          <span>•</span>
          <span>Up to 5 files per batch</span>
        </div>
      </div>

      {/* General Alert / Warning Banner */}
      {generalWarning && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            padding: '12px 16px',
            backgroundColor: 'var(--status-partial-bg)',
            border: '1px solid var(--status-partial-border)',
            borderRadius: 'var(--radius-md)',
            color: 'var(--status-partial-text)',
            fontSize: '14px',
            marginTop: '16px',
          }}
        >
          <AlertTriangle size={18} style={{ flexShrink: 0 }} />
          <span>{generalWarning}</span>
        </div>
      )}

      {/* General Error Banner */}
      {generalError && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            padding: '12px 16px',
            backgroundColor: 'var(--status-error-bg)',
            border: '1px solid var(--status-error-border)',
            borderRadius: 'var(--radius-md)',
            color: 'var(--status-error-text)',
            fontSize: '14px',
            marginTop: '16px',
          }}
        >
          <AlertTriangle size={18} style={{ flexShrink: 0 }} />
          <span>{generalError}</span>
        </div>
      )}

      {/* Selected Documents Queue Section */}
      {selectedFiles.length > 0 && (
        <div style={{ marginTop: '24px' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '12px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h4 style={{ margin: 0, fontSize: '15px', color: 'var(--text-main)', fontWeight: 600 }}>
                Selected Documents Queue
              </h4>
              <span
                style={{
                  fontSize: '12px',
                  fontWeight: 600,
                  backgroundColor: 'var(--primary-blush-light)',
                  color: 'var(--primary-blush)',
                  padding: '2px 8px',
                  borderRadius: '12px',
                }}
              >
                {selectedFiles.length} / {maxFiles} Files ({formatFileSize(totalSizeBytes)})
              </span>
            </div>

            <div style={{ display: 'flex', gap: '10px' }}>
              {selectedFiles.length < maxFiles && (
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isUploading}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '6px 12px',
                    fontSize: '13px',
                    backgroundColor: 'transparent',
                    border: '1px solid var(--border-blush)',
                    borderRadius: 'var(--radius-sm)',
                    color: 'var(--primary-blush)',
                    cursor: isUploading ? 'not-allowed' : 'pointer',
                  }}
                >
                  <PlusCircle size={14} /> Add More
                </button>
              )}
              <button
                type="button"
                onClick={handleClearAll}
                disabled={isUploading}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '6px 12px',
                  fontSize: '13px',
                  backgroundColor: 'transparent',
                  border: '1px solid var(--border-blush)',
                  borderRadius: 'var(--radius-sm)',
                  color: 'var(--text-muted)',
                  cursor: isUploading ? 'not-allowed' : 'pointer',
                }}
              >
                <Trash2 size={14} /> Clear All
              </button>
            </div>
          </div>

          {/* Queue List */}
          <div>
            {selectedFiles.map((item, idx) => (
              <DocumentQueueItem
                key={item.id}
                item={item}
                index={idx}
                onRemove={handleRemove}
                onTypeChange={handleTypeChange}
                onReplaceFile={handleReplaceFile}
                disabled={isUploading}
              />
            ))}
          </div>

          {/* Progress Bar (when uploading) */}
          {isUploading && (
            <div style={{ marginTop: '16px' }}>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  fontSize: '13px',
                  color: 'var(--text-muted)',
                  marginBottom: '6px',
                }}
              >
                <span>{progressStage}</span>
                <span>{uploadProgress}%</span>
              </div>
              <div
                style={{
                  height: '8px',
                  backgroundColor: 'var(--bg-subtle)',
                  borderRadius: '4px',
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    height: '100%',
                    width: `${uploadProgress}%`,
                    backgroundColor: 'var(--primary-blush)',
                    transition: 'width 0.4s ease',
                  }}
                />
              </div>
            </div>
          )}

          {/* Submit Action Bar */}
          <div
            style={{
              marginTop: '20px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '16px',
              backgroundColor: 'var(--bg-surface)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-blush)',
              boxShadow: 'var(--shadow-sm)',
            }}
          >
            <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
              Ready to verify {selectedFiles.length} customs {selectedFiles.length === 1 ? 'document' : 'documents'}.
            </div>

            <button
              type="button"
              onClick={handleSubmitBatch}
              disabled={isUploading || hasInvalidFilesInQueue || selectedFiles.length === 0}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px 24px',
                fontSize: '15px',
                fontWeight: 600,
                color: '#ffffff',
                backgroundColor:
                  isUploading || hasInvalidFilesInQueue
                    ? 'var(--text-subtle)'
                    : 'var(--primary-blush)',
                border: 'none',
                borderRadius: 'var(--radius-sm)',
                cursor:
                  isUploading || hasInvalidFilesInQueue ? 'not-allowed' : 'pointer',
                boxShadow: isUploading ? 'none' : '0 2px 8px rgba(184, 50, 83, 0.25)',
                transition: 'all 0.2s ease',
              }}
            >
              {isUploading ? (
                <>
                  <Loader2 size={18} className="spin" style={{ animation: 'spin 1s linear infinite' }} />
                  <span>Processing Batch...</span>
                </>
              ) : (
                <>
                  <ShieldCheck size={18} />
                  <span>Upload & Verify Batch</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Helpful Document Guidelines */}
      {selectedFiles.length === 0 && (
        <div
          style={{
            marginTop: '28px',
            padding: '20px',
            backgroundColor: 'var(--bg-subtle)',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-blush)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', marginBottom: '10px', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <HelpCircle size={18} color="var(--primary-blush)" />
              <h4 style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: 'var(--text-main)' }}>
                Standard 5 Export Customs Documents
              </h4>
            </div>
            <button
              type="button"
              id="load-sample-pdfs-btn"
              onClick={handleLoadSampleBatch}
              disabled={isUploading}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 12px',
                fontSize: '12px',
                fontWeight: 600,
                backgroundColor: 'var(--bg-surface)',
                color: 'var(--primary-blush)',
                border: '1px solid var(--border-blush)',
                borderRadius: 'var(--radius-sm)',
                cursor: isUploading ? 'not-allowed' : 'pointer',
              }}
              title="Queues 5 valid sample export PDF files for testing live backend batch upload"
            >
              <FilePlus2 size={14} /> Load Sample Trade PDFs (5)
            </button>
          </div>
          <p style={{ margin: '0 0 12px 0', fontSize: '13px', color: 'var(--text-muted)' }}>
            For comprehensive cross-document reconciliation and statutory compliance under Indian Customs Act and DGFT FTP 2023, you can upload any combination of the following:
          </p>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
              gap: '10px',
              fontSize: '13px',
            }}
          >
            <div style={{ padding: '8px 12px', backgroundColor: '#ffffff', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-blush)' }}>
              <strong>1. Commercial Invoice</strong> — Prices, Incoterms, LUT ARN
            </div>
            <div style={{ padding: '8px 12px', backgroundColor: '#ffffff', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-blush)' }}>
              <strong>2. Packing List</strong> — Weights, quantities, packages
            </div>
            <div style={{ padding: '8px 12px', backgroundColor: '#ffffff', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-blush)' }}>
              <strong>3. Purchase Order</strong> — Buyer specifications, agreed terms
            </div>
            <div style={{ padding: '8px 12px', backgroundColor: '#ffffff', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-blush)' }}>
              <strong>4. Shipping Bill</strong> — ICEGATE export declaration, port
            </div>
            <div style={{ padding: '8px 12px', backgroundColor: '#ffffff', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-blush)' }}>
              <strong>5. Certificate of Origin</strong> — Trade agreement origin criteria
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
