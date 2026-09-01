import React, { useState, useEffect } from 'react';
import { documentService, systemService } from '../api/client';
import {
  Upload,
  FileText,
  Trash2,
  Download,
  Activity,
  Layers,
  Clock,
  Zap,
  CheckCircle,
  AlertCircle,
  FileUp,
  RefreshCw
} from 'lucide-react';

export default function AdminPage() {
  const [documents, setDocuments] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [loadingDocs, setLoadingDocs] = useState(true);
  const [loadingMetrics, setLoadingMetrics] = useState(true);

  // Upload form state
  const [selectedFile, setSelectedFile] = useState(null);
  const [category, setCategory] = useState('General');
  const [uploading, setUploading] = useState(false);
  const [uploadFeedback, setUploadFeedback] = useState(null);

  // General error/action states
  const [actionError, setActionError] = useState('');
  const [reindexSuccess, setReindexSuccess] = useState('');
  const [reindexing, setReindexing] = useState(false);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    loadAllData();
  }, []);

  const loadAllData = async () => {
    loadDocuments();
    loadMetrics();
  };

  const loadDocuments = async () => {
    setLoadingDocs(true);
    try {
      const data = await documentService.getDocuments();
      setDocuments(data);
    } catch (err) {
      setActionError(err.response?.data?.detail || 'Failed to load documents');
    } finally {
      setLoadingDocs(false);
    }
  };

  const loadMetrics = async () => {
    setLoadingMetrics(true);
    try {
      const data = await systemService.getMetrics();
      setMetrics(data);
    } catch (err) {
      // Telemetry might be empty initially
    } finally {
      setLoadingMetrics(false);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setUploadFeedback(null);
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!selectedFile) return;

    setUploading(true);
    setUploadFeedback(null);
    setActionError('');

    try {
      const res = await documentService.uploadDocument(selectedFile, category.trim() || 'General');
      setUploadFeedback({
        type: res.cache_hit ? 'info' : 'success',
        message: res.message,
        cache_hit: res.cache_hit,
        chunks_created: res.chunks_created
      });
      setSelectedFile(null);
      // Reset input element
      const fileInput = document.getElementById('admin-file-input');
      if (fileInput) fileInput.value = '';

      loadAllData();
    } catch (err) {
      setActionError(err.response?.data?.detail || 'Failed to upload document');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id, fileName) => {
    if (!window.confirm(`Are you sure you want to delete "${fileName}"? This will rebuild the vector index.`)) {
      return;
    }

    setActionError('');
    try {
      await documentService.deleteDocument(id);
      loadAllData();
    } catch (err) {
      setActionError(err.response?.data?.detail || 'Failed to delete document');
    }
  };

  const handleReindex = async () => {
    setReindexing(true);
    setActionError('');
    setReindexSuccess('');
    try {
      const res = await documentService.reindexDocuments();
      setReindexSuccess(
        `Successfully re-indexed ${res.documents_indexed} documents (${res.chunks_indexed} chunks in FAISS).`
      );
      loadAllData();
    } catch (err) {
      setActionError(err.response?.data?.detail || 'Failed to re-index documents');
    } finally {
      setReindexing(false);
    }
  };

  const handleExportCsv = async () => {
    setExporting(true);
    setActionError('');
    try {
      const blob = await systemService.exportMetricsCsv();
      const url = window.URL.createObjectURL(new Blob([blob]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `query_logs_${new Date().toISOString().slice(0, 10)}.csv`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
    } catch (err) {
      setActionError(err.response?.data?.detail || 'Failed to export telemetry CSV');
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="admin-page-container">
      {/* Top Banner */}
      <div className="admin-header-panel">
        <div className="admin-title-group">
          <h1 className="admin-main-title">Admin Management Console</h1>
          <p className="admin-main-desc">
            Ingest corporate policies, monitor retrieval telemetry, and manage FAISS vector indexing.
          </p>
        </div>

        <div className="admin-header-actions">
          <button className="btn-refresh" onClick={loadAllData} title="Refresh Data">
            <RefreshCw size={15} />
            <span>Refresh</span>
          </button>

          <button
            className="btn-refresh"
            onClick={handleReindex}
            disabled={reindexing}
            title="Trigger Re-indexing of all documents"
          >
            <Layers size={15} />
            <span>{reindexing ? 'Re-indexing...' : 'Trigger Re-index'}</span>
          </button>

          <button
            className="btn-export-csv"
            onClick={handleExportCsv}
            disabled={exporting}
          >
            <Download size={15} />
            <span>{exporting ? 'Exporting...' : 'Export Telemetry CSV'}</span>
          </button>
        </div>
      </div>

      {reindexSuccess && (
        <div className="alert-box success">
          <CheckCircle size={16} />
          <span>{reindexSuccess}</span>
        </div>
      )}

      {actionError && (
        <div className="alert-box error">
          <AlertCircle size={16} />
          <span>{actionError}</span>
        </div>
      )}

      {/* Telemetry Metrics Overview Grid */}
      <div className="metrics-dashboard-grid">
        <div className="metric-card">
          <div className="metric-card-header">
            <span className="metric-label">Total Documents</span>
            <FileText size={18} color="#2563eb" />
          </div>
          <div className="metric-card-value">
            {metrics ? metrics.total_documents : '0'}
          </div>
          <span className="metric-footer">Ingested & indexed files</span>
        </div>

        <div className="metric-card">
          <div className="metric-card-header">
            <span className="metric-label">FAISS Chunks</span>
            <Layers size={18} color="#059669" />
          </div>
          <div className="metric-card-value">
            {metrics ? metrics.total_chunks : '0'}
          </div>
          <span className="metric-footer">768-dim normalized vectors</span>
        </div>

        <div className="metric-card">
          <div className="metric-card-header">
            <span className="metric-label">Queries Served</span>
            <Activity size={18} color="#7c3aed" />
          </div>
          <div className="metric-card-value">
            {metrics ? metrics.total_queries_served : '0'}
          </div>
          <span className="metric-footer">Logged user searches</span>
        </div>

        <div className="metric-card">
          <div className="metric-card-header">
            <span className="metric-label">Median Latency</span>
            <Clock size={18} color="#d97706" />
          </div>
          <div className="metric-card-value">
            {metrics ? `${metrics.latency.median_ms} ms` : '0 ms'}
          </div>
          <span className="metric-footer">p95: {metrics ? `${metrics.latency.p95_ms} ms` : '0 ms'}</span>
        </div>

        <div className="metric-card">
          <div className="metric-card-header">
            <span className="metric-label">Cache Hit Rate</span>
            <Zap size={18} color="#0284c7" />
          </div>
          <div className="metric-card-value">
            {metrics ? `${metrics.cache_hit_rate_pct}%` : '0%'}
          </div>
          <span className="metric-footer">SHA-256 hash matches</span>
        </div>
      </div>

      {/* Main Admin Content: Document Uploader & Table */}
      <div className="admin-content-grid">
        {/* Document Ingestion Card */}
        <div className="admin-panel-card">
          <div className="panel-card-header">
            <div className="panel-header-icon">
              <FileUp size={18} color="#2563eb" />
            </div>
            <h3 className="panel-title">Upload & Ingest Document</h3>
          </div>

          <form onSubmit={handleUpload} className="upload-form">
            <div className="form-group">
              <label className="form-label" htmlFor="admin-file-input">
                Select Document (.txt, .md, .pdf, .docx)
              </label>
              <input
                id="admin-file-input"
                type="file"
                className="file-input-control"
                accept=".txt,.md,.pdf,.docx"
                onChange={handleFileChange}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="category-input">
                Document Category
              </label>
              <input
                id="category-input"
                type="text"
                className="form-input"
                placeholder="e.g. HR, Engineering, Operations"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              />
            </div>

            {uploadFeedback && (
              <div className={`alert-box ${uploadFeedback.type}`}>
                <CheckCircle size={16} />
                <div>
                  <strong>{uploadFeedback.message}</strong>
                  {uploadFeedback.cache_hit && (
                    <p className="feedback-subtext">SHA-256 matched an existing document; re-embedding was skipped ($100\%$ cache hit).</p>
                  )}
                  {!uploadFeedback.cache_hit && uploadFeedback.chunks_created > 0 && (
                    <p className="feedback-subtext">Generated {uploadFeedback.chunks_created} vector chunks in FAISS.</p>
                  )}
                </div>
              </div>
            )}

            <button
              type="submit"
              className="btn-primary"
              disabled={uploading || !selectedFile}
            >
              <Upload size={16} />
              <span>{uploading ? 'Processing & Embedding...' : 'Ingest & Index Document'}</span>
            </button>
          </form>
        </div>

        {/* Ingested Documents List Table */}
        <div className="admin-panel-card full-span">
          <div className="panel-card-header">
            <div className="panel-header-icon">
              <FileText size={18} color="#059669" />
            </div>
            <h3 className="panel-title">Ingested Knowledge Documents ({documents.length})</h3>
          </div>

          {loadingDocs ? (
            <div className="table-loading-state">
              <div className="spinner-small" />
              <span>Loading documents...</span>
            </div>
          ) : documents.length === 0 ? (
            <div className="empty-state-box">
              <FileText size={32} color="#94a3b8" />
              <p className="empty-state-title">No documents ingested yet</p>
              <p className="empty-state-desc">Upload corporate policies or guides above to populate the knowledge base.</p>
            </div>
          ) : (
            <div className="table-wrapper">
              <table className="admin-data-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>File Name</th>
                    <th>Category</th>
                    <th>Chunks</th>
                    <th>Ingested At</th>
                    <th className="th-actions">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {documents.map((doc) => (
                    <tr key={doc.id}>
                      <td className="td-id">#{doc.id}</td>
                      <td className="td-filename">
                        <div className="filename-cell">
                          <FileText size={14} className="doc-icon" />
                          <span>{doc.file_name}</span>
                        </div>
                      </td>
                      <td>
                        <span className="category-pill">{doc.category}</span>
                      </td>
                      <td>
                        <span className="chunks-pill">{doc.chunks} chunks</span>
                      </td>
                      <td className="td-date">{doc.created_at}</td>
                      <td className="td-actions">
                        <button
                          className="btn-delete-doc"
                          onClick={() => handleDelete(doc.id, doc.file_name)}
                          title="Delete document and rebuild FAISS index"
                        >
                          <Trash2 size={15} />
                          <span>Delete</span>
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
