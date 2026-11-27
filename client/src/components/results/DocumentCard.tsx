import React, { useState } from 'react';
import { BatchDocumentItem } from '../../types/batch';
import {
  FileCheck,
  AlertOctagon,
  Copy,
  ChevronDown,
  ChevronUp,
  FileText,
  Building,
  DollarSign,
  PackageCheck,
} from 'lucide-react';

interface DocumentCardProps {
  document: BatchDocumentItem;
  index: number;
}

export const DocumentCard: React.FC<DocumentCardProps> = ({ document, index }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const isSuccess = document.status === 'SUCCESS';
  const isDuplicate = document.status === 'DUPLICATE';
  const isFailed = document.status === 'FAILED';

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getStatusBadge = () => {
    if (isSuccess) {
      return (
        <span
          style={{
            backgroundColor: 'var(--status-success-bg)',
            color: 'var(--status-success-text)',
            border: '1px solid var(--status-success-border)',
            padding: '4px 10px',
            borderRadius: '12px',
            fontSize: '12px',
            fontWeight: 600,
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
          }}
        >
          <FileCheck size={13} /> SUCCESS
        </span>
      );
    }
    if (isDuplicate) {
      return (
        <span
          style={{
            backgroundColor: 'var(--status-partial-bg)',
            color: 'var(--status-partial-text)',
            border: '1px solid var(--status-partial-border)',
            padding: '4px 10px',
            borderRadius: '12px',
            fontSize: '12px',
            fontWeight: 600,
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
          }}
        >
          <Copy size={13} /> DUPLICATE
        </span>
      );
    }
    return (
      <span
        style={{
          backgroundColor: 'var(--status-error-bg)',
          color: 'var(--status-error-text)',
          border: '1px solid var(--status-error-border)',
          padding: '4px 10px',
          borderRadius: '12px',
          fontSize: '12px',
          fontWeight: 600,
          display: 'inline-flex',
          alignItems: 'center',
          gap: '4px',
        }}
      >
        <AlertOctagon size={13} /> FAILED
      </span>
    );
  };

  const extracted = document.extracted_data;

  return (
    <div
      style={{
        backgroundColor: 'var(--bg-surface)',
        border: `1px solid ${isFailed ? 'var(--status-error-border)' : 'var(--border-blush)'}`,
        borderRadius: 'var(--radius-md)',
        padding: '16px 20px',
        marginBottom: '14px',
        boxShadow: 'var(--shadow-sm)',
        transition: 'all 0.2s ease',
      }}
    >
      {/* Header Row */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          cursor: isSuccess ? 'pointer' : 'default',
        }}
        onClick={() => isSuccess && setIsExpanded(!isExpanded)}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', minWidth: 0, flex: 1 }}>
          <div
            style={{
              width: '40px',
              height: '40px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: isSuccess
                ? 'var(--primary-blush-light)'
                : isDuplicate
                ? 'var(--status-partial-bg)'
                : 'var(--status-error-bg)',
              color: isSuccess
                ? 'var(--primary-blush)'
                : isDuplicate
                ? 'var(--status-partial-text)'
                : 'var(--status-error-text)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            <FileText size={20} />
          </div>

          <div style={{ minWidth: 0, flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '12px', color: 'var(--text-subtle)', fontWeight: 600 }}>
                Doc #{index + 1}
              </span>
              <strong style={{ fontSize: '14px', color: 'var(--text-main)' }}>
                {document.original_filename}
              </strong>
              {document.document_type && (
                <span
                  style={{
                    backgroundColor: 'var(--bg-subtle)',
                    color: 'var(--primary-blush)',
                    border: '1px solid var(--border-blush)',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontSize: '12px',
                    fontWeight: 500,
                  }}
                >
                  {document.document_type}
                </span>
              )}
              {document.fallback_used && (
                <span
                  style={{
                    backgroundColor: 'var(--status-partial-bg)',
                    color: 'var(--status-partial-text)',
                    border: '1px solid var(--status-partial-border)',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontSize: '11px',
                    fontWeight: 600,
                  }}
                >
                  PyMuPDF Fallback (Non-AI)
                </span>
              )}
            </div>

            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
              <span>Size: {formatFileSize(document.file_size_bytes)}</span>
              {document.saved_filename && (
                <span style={{ marginLeft: '12px', color: 'var(--text-subtle)' }}>
                  Stored: {document.saved_filename}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Right side status & expand toggle */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginLeft: '12px' }}>
          {getStatusBadge()}
          {isSuccess && (
            <button
              type="button"
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                padding: '4px',
                display: 'flex',
                alignItems: 'center',
              }}
              aria-label={isExpanded ? 'Collapse' : 'Expand'}
            >
              {isExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
            </button>
          )}
        </div>
      </div>

      {/* Warning Callout if Non-AI Fallback Used */}
      {document.warning && (
        <div
          style={{
            marginTop: '12px',
            padding: '10px 14px',
            backgroundColor: 'var(--status-partial-bg)',
            border: '1px solid var(--status-partial-border)',
            borderRadius: 'var(--radius-sm)',
            fontSize: '13px',
            color: 'var(--status-partial-text)',
          }}
        >
          <strong>Fallback Notice:</strong> {document.warning}
        </div>
      )}

      {/* Error Callout if Failed */}
      {document.error && (
        <div
          style={{
            marginTop: '12px',
            padding: '10px 14px',
            backgroundColor: 'var(--status-error-bg)',
            border: '1px solid var(--status-error-border)',
            borderRadius: 'var(--radius-sm)',
            fontSize: '13px',
            color: 'var(--status-error-text)',
          }}
        >
          <strong>{document.error_code || 'Error'}:</strong> {document.error}
        </div>
      )}

      {/* Extracted Structured Intelligence Details (Expandable) */}
      {isSuccess && isExpanded && extracted && (
        <div
          style={{
            marginTop: '16px',
            paddingTop: '16px',
            borderTop: '1px solid var(--border-subtle)',
            fontSize: '13px',
          }}
        >
          <div style={{ fontWeight: 600, color: 'var(--text-main)', marginBottom: '10px' }}>
            Gemini Extracted Intelligence:
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
              gap: '12px',
              marginBottom: '14px',
            }}
          >
            {/* Exporter / Seller */}
            {(extracted.exporter_seller || extracted.exporter || extracted.vendor_supplier) && (() => {
              const exp = extracted.exporter_seller || extracted.exporter || extracted.vendor_supplier;
              return (
                <div
                  style={{
                    padding: '10px 12px',
                    backgroundColor: 'var(--bg-subtle)',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border-blush)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--primary-blush)', fontWeight: 600, marginBottom: '4px' }}>
                    <Building size={14} /> Exporter / Seller
                  </div>
                  <div style={{ fontWeight: 500 }}>{exp.name || 'N/A'}</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    IEC / Tax: {exp.tax_id_or_gstin || exp.iec || extracted.iec || 'N/A'}
                  </div>
                </div>
              );
            })()}

            {/* Consignee / Importer / Buyer */}
            {(extracted.consignee_importer || extracted.consignee || extracted.importer_or_consignee || extracted.buyer) && (() => {
              const cons = extracted.consignee_importer || extracted.consignee || extracted.importer_or_consignee || extracted.buyer;
              return (
                <div
                  style={{
                    padding: '10px 12px',
                    backgroundColor: 'var(--bg-subtle)',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border-blush)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--primary-blush)', fontWeight: 600, marginBottom: '4px' }}>
                    <Building size={14} /> Consignee / Importer
                  </div>
                  <div style={{ fontWeight: 500 }}>{cons.name || 'N/A'}</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    Country: {cons.country || extracted.country_of_destination || 'N/A'}
                  </div>
                </div>
              );
            })()}

            {/* Financial / Reference Values */}
            {(extracted.invoice_number ||
              extracted.po_number ||
              extracted.shipping_bill_number ||
              extracted.certificate_number ||
              extracted.total_invoice_amount !== undefined ||
              extracted.total_invoice_value !== undefined ||
              extracted.total_amount !== undefined ||
              extracted.fob_value !== undefined) && (() => {
              const refNo =
                extracted.invoice_number ||
                extracted.po_number ||
                extracted.shipping_bill_number ||
                extracted.certificate_number ||
                extracted.packing_list_number;
              const amount =
                extracted.total_invoice_amount ??
                extracted.total_invoice_value ??
                extracted.total_amount ??
                extracted.fob_value;
              return (
                <div
                  style={{
                    padding: '10px 12px',
                    backgroundColor: 'var(--bg-subtle)',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border-blush)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--primary-blush)', fontWeight: 600, marginBottom: '4px' }}>
                    <DollarSign size={14} /> Reference & Valuation
                  </div>
                  <div>Ref No: {refNo || 'N/A'}</div>
                  <div>
                    Amount: {extracted.currency || ''} {amount ?? 'N/A'} ({extracted.incoterms || extracted.customs_port_code || extracted.origin_criterion || 'Standard'})
                  </div>
                </div>
              );
            })()}

            {/* Packing / Shipping Metrics */}
            {(extracted.total_packages_count !== undefined ||
              extracted.total_packages !== undefined ||
              extracted.total_gross_weight !== undefined ||
              extracted.gross_weight !== undefined ||
              extracted.total_gross_weight_kg !== undefined) && (() => {
              const pkg = extracted.total_packages_count ?? extracted.total_packages;
              const grossRaw = extracted.total_gross_weight ?? extracted.gross_weight ?? extracted.total_gross_weight_kg;
              const netRaw = extracted.total_net_weight ?? extracted.net_weight ?? extracted.total_net_weight_kg;
              const fmtW = (w: any) =>
                w && typeof w === 'object' ? `${w.value ?? 'N/A'} ${w.unit || 'KG'}` : (w !== undefined && w !== null ? `${w} KG` : 'N/A');
              return (
                <div
                  style={{
                    padding: '10px 12px',
                    backgroundColor: 'var(--bg-subtle)',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border-blush)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--primary-blush)', fontWeight: 600, marginBottom: '4px' }}>
                    <PackageCheck size={14} /> Packing Metrics
                  </div>
                  <div>Total Packages: {pkg ?? 'N/A'}</div>
                  <div>
                    Gross Wt: {fmtW(grossRaw)} | Net Wt: {fmtW(netRaw)}
                  </div>
                </div>
              );
            })()}
          </div>

          {/* Raw JSON viewer */}
          <details style={{ marginTop: '8px' }}>
            <summary style={{ cursor: 'pointer', color: 'var(--primary-blush)', fontSize: '12px', fontWeight: 600 }}>
              View Complete Extracted JSON Payload
            </summary>
            <pre
              style={{
                backgroundColor: 'var(--bg-subtle)',
                padding: '12px',
                borderRadius: 'var(--radius-sm)',
                overflowX: 'auto',
                fontSize: '11px',
                border: '1px solid var(--border-blush)',
                marginTop: '8px',
                color: 'var(--text-main)',
              }}
            >
              {JSON.stringify(extracted, null, 2)}
            </pre>
          </details>
        </div>
      )}
    </div>
  );
};
