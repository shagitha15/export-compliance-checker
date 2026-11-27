import { BatchUploadResponse } from '../types/batch';
import { API_ENDPOINTS } from '../constants/apiEndpoints';
import { FraudAnalysisReport } from '../features/compliance/types';
import { authenticatedFetch, ensureValidAccessToken } from './authService';
import { authStorage } from './authStorage';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';

export class BatchUploadError extends Error {
  public statusCode?: number;
  public details?: any;

  constructor(message: string, statusCode?: number, details?: any) {
    super(message);
    this.name = 'BatchUploadError';
    this.statusCode = statusCode;
    this.details = details;
  }
}

function extractRealShipmentDetails(response: BatchUploadResponse): Record<string, any> {
  const docsByType: Record<string, Record<string, any>> = {};
  for (const doc of response.documents) {
    if (doc.status === 'SUCCESS' && doc.document_type && doc.extracted_data) {
      docsByType[doc.document_type] = doc.extracted_data;
    }
  }

  const ci = docsByType['Commercial Invoice'] || {};
  const sb = docsByType['Shipping Bill'] || {};
  const po = docsByType['Purchase Order'] || {};
  const coo = docsByType['Certificate of Origin'] || {};
  const pl = docsByType['Packing List'] || {};

  const exporter = ci.exporter_seller || sb.exporter || coo.exporter || pl.exporter_seller || {};
  const consignee =
    ci.consignee_importer || sb.consignee || coo.importer_or_consignee || pl.consignee || po.buyer || {};

  const rawAmount =
    ci.total_invoice_amount ??
    ci.total_invoice_value ??
    ci.subtotal ??
    sb.fob_value ??
    sb.total_invoice_value ??
    po.total_amount ??
    null;

  return {
    exporter_name: exporter.name || null,
    exporter_iec: exporter.iec || sb.iec || null,
    exporter_gstin: exporter.tax_id_or_gstin || sb.gstin || null,
    consignee_name: consignee.name || null,
    destination_country:
      consignee.country ||
      sb.country_of_destination ||
      response.government_compliance?.destination_country ||
      null,
    invoice_number: ci.invoice_number || sb.invoice_number || pl.invoice_reference_number || null,
    declared_currency: ci.currency || sb.currency || po.currency || null,
    total_declared_value: typeof rawAmount === 'number' ? rawAmount : null,
    incoterms: ci.incoterms || po.incoterms || null,
  };
}

/**
 * Service to execute multi-document batch uploads and batch PDF report downloads.
 */
export const batchService = {
  /**
   * Uploads up to 5 PDF documents using multipart/form-data.
   */
  async uploadBatch(
    files: File[],
    documentTypes?: string[],
    onProgress?: (percent: number, stageLabel?: string) => void
  ): Promise<BatchUploadResponse> {
    if (!files || files.length === 0) {
      throw new BatchUploadError('No files selected for batch upload.', 400);
    }

    if (files.length > 5) {
      throw new BatchUploadError(
        `Batch limit exceeded: Maximum 5 documents permitted, but received ${files.length}.`,
        400
      );
    }

    const formData = new FormData();

    // Append each file under form field name "files"
    files.forEach((file) => {
      formData.append('files', file, file.name);
    });

    // Append optional document types if provided
    if (documentTypes && documentTypes.length > 0) {
      documentTypes.forEach((docType) => {
        if (docType && docType !== 'Auto-Detect') {
          formData.append('document_types', docType);
        } else {
          formData.append('document_types', '');
        }
      });
    }

    const url = `${BASE_URL}${API_ENDPOINTS.DOCUMENTS.BATCH_UPLOAD}`;

    await ensureValidAccessToken(false);

    // Use XMLHttpRequest when available for real upload byte progress
    if (typeof XMLHttpRequest !== 'undefined') {
      const executeXhr = (allowRetryOn401: boolean): Promise<BatchUploadResponse> =>
        new Promise<BatchUploadResponse>((resolve, reject) => {
          const usedToken = authStorage.getAccessToken();
          const xhr = new XMLHttpRequest();
          xhr.open('POST', url, true);
          xhr.setRequestHeader('Accept', 'application/json');
          Object.entries(authStorage.getAuthHeaders()).forEach(([k, v]) => {
            xhr.setRequestHeader(k, v);
          });

          xhr.upload.onprogress = (event) => {
            if (event.lengthComputable && onProgress) {
              const uploadPct = Math.min(60, Math.max(5, Math.round((event.loaded / event.total) * 60)));
              onProgress(uploadPct, 'Uploading PDFs via multipart/form-data...');
            }
          };

          xhr.upload.onload = () => {
            if (onProgress) {
              onProgress(70, 'Processing OCR, AI Extraction & Compliance Audit...');
            }
          };

          xhr.onload = async () => {
            if (xhr.status === 401 && allowRetryOn401 && authStorage.getRefreshToken()) {
              try {
                if (onProgress) {
                  onProgress(15, 'Refreshing authentication session...');
                }
                await ensureValidAccessToken(true, usedToken);
                const retried = await executeXhr(false);
                resolve(retried);
                return;
              } catch (refreshErr: any) {
                reject(
                  new BatchUploadError(
                    refreshErr?.message || 'Your session has expired. Please sign in again.',
                    401,
                    refreshErr
                  )
                );
                return;
              }
            }

            if (xhr.status === 401 && usedToken) {
              authStorage.clear();
              authStorage.notifySessionExpired('Your session has expired. Please sign in again.');
            }

            let responseData: any;
            try {
              responseData = JSON.parse(xhr.responseText || '{}');
            } catch {
              reject(
                new BatchUploadError(
                  `Server returned non-JSON response (HTTP ${xhr.status}).`,
                  xhr.status
                )
              );
              return;
            }

            if (xhr.status < 200 || xhr.status >= 300) {
              const errorDetail =
                responseData.detail ||
                responseData.message ||
                `Batch processing failed with status ${xhr.status}`;
              reject(
                new BatchUploadError(
                  typeof errorDetail === 'string' ? errorDetail : JSON.stringify(errorDetail),
                  xhr.status,
                  responseData
                )
              );
              return;
            }

            if (onProgress) {
              onProgress(100, 'Batch verification complete.');
            }
            resolve(responseData as BatchUploadResponse);
          };

          xhr.onerror = () => {
            reject(
              new BatchUploadError(
                'Unable to connect to the backend server. Please verify the service is running.',
                0
              )
            );
          };

          xhr.send(formData);
        });

      return executeXhr(true);
    }

    try {
      // Note: Do NOT set 'Content-Type' header so fetch sets the multipart boundary automatically.
      const response = await authenticatedFetch(url, {
        method: 'POST',
        headers: {
          Accept: 'application/json',
        },
        body: formData,
      });

      let responseData: any;
      try {
        responseData = await response.json();
      } catch {
        throw new BatchUploadError(
          `Server returned non-JSON response (HTTP ${response.status}).`,
          response.status
        );
      }

      if (!response.ok) {
        const errorDetail =
          responseData.detail ||
          responseData.message ||
          `Batch processing failed with status ${response.status}`;
        throw new BatchUploadError(
          typeof errorDetail === 'string' ? errorDetail : JSON.stringify(errorDetail),
          response.status,
          responseData
        );
      }

      return responseData as BatchUploadResponse;
    } catch (err: any) {
      if (err instanceof BatchUploadError) {
        throw err;
      }
      throw new BatchUploadError(
        err.message || 'Unable to connect to the backend server. Please verify the service is running.',
        0,
        err
      );
    }
  },

  /**
   * Generates and downloads a PDF Compliance Report for a completed batch upload
   * via POST /api/v1/compliance/report/pdf.
   */
  async downloadBatchPdfReport(
    response: BatchUploadResponse,
    fraudReport?: FraudAnalysisReport | null
  ): Promise<string> {
    const extractedDocuments: Record<string, Record<string, any>> = {};
    for (const doc of response.documents) {
      if (doc.status === 'SUCCESS' && doc.document_type && doc.extracted_data) {
        extractedDocuments[doc.document_type] = doc.extracted_data;
      }
    }

    const uploadedDocuments = response.documents.map((d) => ({
      original_filename: d.original_filename,
      saved_filename: d.saved_filename || null,
      document_type: d.document_type || null,
      status: d.status,
      file_size_bytes: d.file_size_bytes,
      error: d.error || null,
      error_code: d.error_code || null,
    }));

    const payload = {
      batch_id: response.batch_id,
      batch_status: response.batch_status,
      report_generated_at: response.timestamp,
      shipment_details: extractRealShipmentDetails(response),
      uploaded_documents: uploadedDocuments,
      extracted_documents: Object.keys(extractedDocuments).length > 0 ? extractedDocuments : null,
      cross_document_validation: response.cross_document_validation || null,
      government_compliance: response.government_compliance || null,
      fraud_analysis: fraudReport || null,
      scenario_title: `Batch Upload Audit (${response.batch_id})`,
    };

    const url = `${BASE_URL}${API_ENDPOINTS.COMPLIANCE.PDF_REPORT}`;
    const res = await authenticatedFetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/pdf',
      },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const errBody = await res.json().catch(() => ({}));
      throw new Error(errBody.detail || `Failed to generate PDF report (HTTP ${res.status})`);
    }

    const blob = await res.blob();
    if (!blob || blob.size === 0) {
      throw new Error('Server returned an empty PDF document.');
    }

    const filename = `compliance_report_${response.batch_id || 'batch'}.pdf`;
    const downloadUrl = window.URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = downloadUrl;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.URL.revokeObjectURL(downloadUrl);

    return filename;
  },
};
