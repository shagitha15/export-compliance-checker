import React from 'react';
import { SelectedFileItem } from '../../types/batch';
import { DOCUMENT_TYPES } from '../../constants/documentTypes';
import { FileText, Trash2, RefreshCw, AlertCircle, CheckCircle2 } from 'lucide-react';

interface DocumentQueueItemProps {
  item: SelectedFileItem;
  index: number;
  onRemove: (id: string) => void;
  onTypeChange: (id: string, newType: string) => void;
  onReplaceFile: (id: string, newFile: File) => void;
  disabled?: boolean;
}

export const DocumentQueueItem: React.FC<DocumentQueueItemProps> = ({
  item,
  index,
  onRemove,
  onTypeChange,
  onReplaceFile,
  disabled = false,
}) => {
  const replaceInputRef = React.useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      onReplaceFile(item.id, e.target.files[0]);
    }
  };

  const hasError = !!item.validationError;

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '12px 16px',
        backgroundColor: hasError ? 'var(--status-error-bg)' : 'var(--bg-surface)',
        border: `1px solid ${hasError ? 'var(--status-error-border)' : 'var(--border-blush)'}`,
        borderRadius: 'var(--radius-md)',
        marginBottom: '10px',
        boxShadow: 'var(--shadow-sm)',
        transition: 'all 0.2s ease',
      }}
    >
      {/* Hidden file input for Replace */}
      <input
        type="file"
        ref={replaceInputRef}
        accept=".pdf,application/pdf"
        style={{ display: 'none' }}
        onChange={handleFileChange}
        disabled={disabled}
      />

      {/* Left: Icon & Info */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1, minWidth: 0 }}>
        <div
          style={{
            width: '38px',
            height: '38px',
            borderRadius: 'var(--radius-sm)',
            backgroundColor: hasError ? 'rgba(239, 68, 68, 0.1)' : 'var(--primary-blush-light)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: hasError ? 'var(--status-error-text)' : 'var(--primary-blush)',
            flexShrink: 0,
          }}
        >
          {hasError ? <AlertCircle size={20} /> : <FileText size={20} />}
        </div>

        <div style={{ minWidth: 0, flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span
              style={{
                fontSize: '11px',
                fontWeight: 600,
                color: 'var(--text-subtle)',
                backgroundColor: 'var(--bg-subtle)',
                padding: '2px 6px',
                borderRadius: '4px',
              }}
            >
              #{index + 1}
            </span>
            <span
              style={{
                fontSize: '14px',
                fontWeight: 600,
                color: 'var(--text-main)',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
              title={item.file.name}
            >
              {item.file.name}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '3px' }}>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              {item.sizeFormatted}
            </span>
            {hasError ? (
              <span
                style={{
                  fontSize: '12px',
                  color: 'var(--status-error-text)',
                  fontWeight: 500,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                }}
              >
                {item.validationError}
              </span>
            ) : (
              <span
                style={{
                  fontSize: '12px',
                  color: 'var(--status-success-text)',
                  fontWeight: 500,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                }}
              >
                <CheckCircle2 size={12} /> Valid PDF
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Right: Type Selector & Actions */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginLeft: '12px' }}>
        <select
          value={item.documentType}
          onChange={(e) => onTypeChange(item.id, e.target.value)}
          disabled={disabled || hasError}
          style={{
            padding: '6px 10px',
            fontSize: '13px',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-blush)',
            backgroundColor: 'var(--bg-subtle)',
            color: 'var(--text-main)',
            outline: 'none',
            cursor: disabled ? 'not-allowed' : 'pointer',
          }}
          title="Select customs document type or allow AI auto-classification"
        >
          <option value="Auto-Detect">Auto-Detect Document Type</option>
          {DOCUMENT_TYPES.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </select>

        {/* Replace Button */}
        <button
          type="button"
          onClick={() => replaceInputRef.current?.click()}
          disabled={disabled}
          title="Replace this document"
          style={{
            padding: '6px 8px',
            border: '1px solid var(--border-blush)',
            backgroundColor: 'transparent',
            borderRadius: 'var(--radius-sm)',
            color: 'var(--text-muted)',
            cursor: disabled ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            fontSize: '12px',
          }}
        >
          <RefreshCw size={14} />
          <span style={{ display: 'none' }}>Replace</span>
        </button>

        {/* Remove Button */}
        <button
          type="button"
          onClick={() => onRemove(item.id)}
          disabled={disabled}
          title="Remove from batch"
          style={{
            padding: '6px 8px',
            border: '1px solid var(--border-blush)',
            backgroundColor: 'var(--primary-blush-subtle)',
            borderRadius: 'var(--radius-sm)',
            color: 'var(--primary-blush)',
            cursor: disabled ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <Trash2 size={14} />
        </button>
      </div>
    </div>
  );
};
