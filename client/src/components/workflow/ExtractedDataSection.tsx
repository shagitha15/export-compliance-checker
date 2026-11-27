import React from 'react';
import { BatchDocumentItem } from '../../types/batch';
import { FileCheck, AlertOctagon, Copy, AlertTriangle } from 'lucide-react';

interface ExtractedDataSectionProps {
  documents: BatchDocumentItem[];
  onGoToUpload: () => void;
}

const MISSING_LABEL = 'Missing / Not Readable';

function formatField(val: any): string {
  if (val === null || val === undefined || val === '') return MISSING_LABEL;
  if (typeof val === 'object') {
    if ('value' in val) {
      return val.value !== null && val.value !== undefined
        ? `${val.value} ${val.unit || ''}`.trim()
        : MISSING_LABEL;
    }
    if ('name' in val) {
      return val.name || MISSING_LABEL;
    }
    return JSON.stringify(val);
  }
  return String(val);
}

function getLineItemsSummary(extracted: Record<string, any>): {
  description: string;
  hsCode: string;
  quantity: string;
} {
  const items = extracted.line_items || extracted.items || extracted.item_details || [];
  if (Array.isArray(items) && items.length > 0) {
    const first = items[0] || {};
    return {
      description:
        first.description ||
        first.description_of_goods ||
        extracted.description_of_goods ||
        MISSING_LABEL,
      hsCode: first.hs_code || first.ritc_hs_code || extracted.hs_code || MISSING_LABEL,
      quantity:
        first.quantity !== undefined && first.quantity !== null
          ? `${first.quantity} ${first.unit || ''}`.trim()
          : first.quantity_or_weight || MISSING_LABEL,
    };
  }
  return {
    description: extracted.description_of_goods || MISSING_LABEL,
    hsCode: extracted.hs_code || MISSING_LABEL,
    quantity:
      extracted.total_packages_count !== undefined && extracted.total_packages_count !== null
        ? `${extracted.total_packages_count} pkgs`
        : MISSING_LABEL,
  };
}

export const ExtractedDataSection: React.FC<ExtractedDataSectionProps> = ({
  documents,
  onGoToUpload,
}) => {
  if (!documents || documents.length === 0) {
    return (
      <div
        style={{
          backgroundColor: 'var(--bg-surface)',
          border: '1px solid var(--border-blush)',
          borderRadius: 'var(--radius-lg)',
          padding: '32px',
          textAlign: 'center',
          boxShadow: 'var(--shadow-sm)',
        }}
      >
        <p style={{ margin: '0 0 14px 0', color: 'var(--text-muted)', fontSize: '14px' }}>
          No documents have been uploaded and extracted yet.
        </p>
        <button
          type="button"
          onClick={onGoToUpload}
          style={{
            padding: '9px 18px',
            fontSize: '13px',
            fontWeight: 700,
            backgroundColor: '#102A43',
            color: '#ffffff',
            border: 'none',
            borderRadius: 'var(--radius-sm)',
            cursor: 'pointer',
          }}
        >
          Go to Upload Documents
        </button>
      </div>
    );
  }

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

      {documents.map((doc, idx) => {
        const extracted = doc.extracted_data || {};
        const isSuccess = doc.status === 'SUCCESS';
        const isDuplicate = doc.status === 'DUPLICATE';
        const itemSummary = getLineItemsSummary(extracted);

        const docNo =
          extracted.invoice_number ||
          extracted.packing_list_number ||
          extracted.shipping_bill_number ||
          extracted.bl_number ||
          extracted.po_number ||
          extracted.certificate_number;

        const currency = extracted.currency;
        const rawVal =
          extracted.total_invoice_amount ??
          extracted.fob_value ??
          extracted.total_invoice_value ??
          extracted.total_amount;
        const valDisplay =
          rawVal !== null && rawVal !== undefined
            ? `${currency || ''} ${rawVal}`.trim()
            : MISSING_LABEL;

        const exporterObj =
          extracted.exporter_seller || extracted.exporter || extracted.vendor_supplier || {};
        const consigneeObj =
          extracted.consignee_importer ||
          extracted.consignee ||
          extracted.importer_or_consignee ||
          extracted.buyer ||
          {};

        const fields: Array<{ label: string; value: string }> = [
          { label: 'Document Number', value: formatField(docNo) },
          { label: 'Product Description', value: itemSummary.description },
          { label: 'HS / RITC Code', value: itemSummary.hsCode },
          { label: 'Quantity / Packages', value: itemSummary.quantity },
          { label: 'Currency', value: formatField(currency) },
          { label: 'Declared Value', value: valDisplay },
          {
            label: 'Net Weight',
            value: formatField(extracted.total_net_weight ?? extracted.net_weight),
          },
          {
            label: 'Gross Weight',
            value: formatField(extracted.total_gross_weight ?? extracted.gross_weight),
          },
          { label: 'Exporter / Seller', value: formatField(exporterObj.name) },
          {
            label: 'Exporter GSTIN / IEC',
            value: formatField(exporterObj.tax_id_or_gstin || extracted.gstin || exporterObj.iec || extracted.iec),
          },
          { label: 'Consignee / Importer', value: formatField(consigneeObj.name) },
          {
            label: 'Incoterms / Port',
            value: formatField(
              extracted.incoterms || extracted.customs_port_code || extracted.port_of_loading
            ),
          },
        ];

        return (
          <div
            key={`${doc.original_filename}_${idx}`}
            style={{
              backgroundColor: 'var(--bg-surface)',
              border: `1px solid ${
                doc.status === 'FAILED' ? 'var(--status-error-border)' : 'var(--border-blush)'
              }`,
              borderRadius: 'var(--radius-md)',
              padding: '18px 22px',
              boxShadow: 'var(--shadow-sm)',
            }}
          >
            {/* Document Header */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: '10px',
                marginBottom: '12px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                <strong style={{ fontSize: '15px', color: 'var(--text-main)' }}>
                  {doc.original_filename}
                </strong>
                {doc.document_type && (
                  <span
                    style={{
                      fontSize: '12px',
                      fontWeight: 600,
                      padding: '2px 8px',
                      borderRadius: '4px',
                      backgroundColor: 'var(--bg-subtle)',
                      color: 'var(--primary-blush)',
                      border: '1px solid var(--border-blush)',
                    }}
                  >
                    {doc.document_type}
                  </span>
                )}
                {doc.extraction_method && (
                  <span
                    style={{
                      fontSize: '11px',
                      fontWeight: 600,
                      padding: '2px 8px',
                      borderRadius: '4px',
                      backgroundColor: doc.fallback_used
                        ? 'var(--status-partial-bg)'
                        : 'var(--primary-blush-light)',
                      color: doc.fallback_used
                        ? 'var(--status-partial-text)'
                        : 'var(--primary-blush)',
                    }}
                  >
                    {doc.fallback_used ? 'PyMuPDF Fallback (Non-AI)' : 'Gemini AI Extracted'}
                  </span>
                )}
              </div>

              <span
                style={{
                  fontSize: '11px',
                  fontWeight: 700,
                  padding: '3px 10px',
                  borderRadius: '12px',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  backgroundColor: isSuccess
                    ? 'var(--status-success-bg)'
                    : isDuplicate
                    ? 'var(--status-partial-bg)'
                    : 'var(--status-error-bg)',
                  color: isSuccess
                    ? 'var(--status-success-text)'
                    : isDuplicate
                    ? 'var(--status-partial-text)'
                    : 'var(--status-error-text)',
                }}
              >
                {isSuccess && <FileCheck size={12} />}
                {isDuplicate && <Copy size={12} />}
                {!isSuccess && !isDuplicate && <AlertOctagon size={12} />}
                {doc.status}
              </span>
            </div>

            {doc.warning && (
              <div
                style={{
                  marginBottom: '12px',
                  padding: '8px 12px',
                  backgroundColor: 'var(--status-partial-bg)',
                  border: '1px solid var(--status-partial-border)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '12px',
                  color: 'var(--status-partial-text)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                <AlertTriangle size={14} /> <span>{doc.warning}</span>
              </div>
            )}

            {doc.error && (
              <div
                style={{
                  marginBottom: '12px',
                  padding: '10px 12px',
                  backgroundColor: 'var(--status-error-bg)',
                  border: '1px solid var(--status-error-border)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '12px',
                  color: 'var(--status-error-text)',
                }}
              >
                <strong>{doc.error_code || 'Extraction Error'}:</strong> {doc.error}
              </div>
            )}

            {isSuccess && doc.extracted_data && (
              <>
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
                    gap: '10px',
                  }}
                >
                  {fields.map((field) => {
                    const isMissing = field.value === MISSING_LABEL;
                    return (
                      <div
                        key={field.label}
                        style={{
                          padding: '8px 10px',
                          backgroundColor: isMissing ? 'var(--status-partial-bg)' : 'var(--bg-subtle)',
                          border: `1px solid ${
                            isMissing ? 'var(--status-partial-border)' : 'var(--border-subtle)'
                          }`,
                          borderRadius: 'var(--radius-sm)',
                        }}
                      >
                        <div style={{ fontSize: '11px', color: 'var(--text-subtle)', fontWeight: 600 }}>
                          {field.label}
                        </div>
                        <div
                          style={{
                            fontSize: '12.5px',
                            fontWeight: isMissing ? 500 : 600,
                            color: isMissing ? 'var(--status-partial-text)' : 'var(--text-main)',
                            marginTop: '2px',
                            wordBreak: 'break-word',
                          }}
                        >
                          {field.value}
                        </div>
                      </div>
                    );
                  })}
                </div>

                <details style={{ marginTop: '12px' }}>
                  <summary style={{ cursor: 'pointer', color: 'var(--primary-blush)', fontSize: '12px', fontWeight: 600 }}>
                    View Complete Extracted JSON
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
                    }}
                  >
                    {JSON.stringify(doc.extracted_data, null, 2)}
                  </pre>
                </details>
              </>
            )}
          </div>
        );
      })}
    </div>
  );
};
