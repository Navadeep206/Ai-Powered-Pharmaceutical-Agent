import api from './api';

/**
 * Service handling document upload and AI-assisted information extraction endpoints.
 */
export const documentService = {
  /**
   * Upload an incident PDF document for text parsing and OCR detection.
   *
   * @param {File} file - Raw File object (PDF)
   * @param {string} [investigationId] - Optional investigation ID to link document metadata
   * @returns {Promise<import('../schemas/types').DocumentExtractionResult>}
   */
  async uploadDocument(file, investigationId = null) {
    if (!file) throw new Error('A valid PDF file is required for upload.');

    const formData = new FormData();
    formData.append('file', file);

    const config = {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: 60000, // 60s timeout for large PDF parsing
    };

    if (investigationId) {
      config.params = { investigation_id: investigationId };
    }

    const response = await api.post('/documents/upload', formData, config);
    return response.data;
  },

  /**
   * Preprocess and normalize multi-modal incident intake.
   *
   * @param {Object} payload - DocumentAnalysisRequest payload
   * @param {boolean} [extract=false] - Whether to trigger LangGraph AI extraction
   * @returns {Promise<Object>}
   */
  async analyzeDocument(payload, extract = false) {
    const response = await api.post('/documents/analyze', payload, {
      params: { extract },
      timeout: extract ? 90000 : 15000,
    });
    return response.data;
  },

  /**
   * Execute LangGraph AI-assisted incident extraction workflow.
   * Supports Document, Text, and Email intake modalities.
   *
   * @param {Object} payload - DocumentAnalysisRequest ({ intake_method, document_id, document_text, text_input, email_input })
   * @param {boolean} [raiseOnError=false] - Whether backend should raise HTTP error on AI provider failure
   * @returns {Promise<Object>} ExtractionAnalysisResponse
   */
  async extractDocument(payload, raiseOnError = false) {
    const response = await api.post('/documents/extract', payload, {
      params: { raise_on_error: raiseOnError },
      timeout: 90000, // 90s extended timeout for LLM and LangGraph reasoning
    });
    return response.data;
  },
};

export default documentService;

