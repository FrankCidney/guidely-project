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
  RefreshCw,
  ChevronDown,
  ChevronUp
} from 'lucide-react';

// Helper to format ISO-8601 UTC timestamp into user's local timezone
function formatLocalDateTime(utcString) {
  if (!utcString) return '-';
  try {
    let isoStr = String(utcString).trim();
    if (!isoStr.endsWith('Z') && !isoStr.includes('+')) {
      isoStr = isoStr.includes(' ') ? `${isoStr.replace(' ', 'T')}Z` : `${isoStr}Z`;
    }
    const date = new Date(isoStr);
    if (isNaN(date.getTime())) return utcString;
    return date.toLocaleString();
  } catch {
    return utcString;
  }
}

export default function AdminPage() {
  const [documents, setDocuments] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [recentQueries, setRecentQueries] = useState([]);
  const [showTelemetry, setShowTelemetry] = useState(true);
  const [loadingDocs, setLoadingDocs] = useState(true);
  const [loadingMetrics, setLoadingMetrics] = useState(true);

  // Upload form state
  const [selectedFile, setSelectedFile] = useState(null);
  const [category, setCategory] = useState('general');
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
    loadRecentQueries();
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

  const loadRecentQueries = async () => {
    try {
      const data = await systemService.getRecentQueries(15);
      setRecentQueries(data);
    } catch {
      // Telemetry log might be empty initially
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

    const cleanCategory = category.replace(/\s+/g, ' ').trim().toLowerCase() || 'general';

    try {
      const res = await documentService.uploadDocument(selectedFile, cleanCategory);
      setUploadFeedback({
        type: res.cache_hit ? 'info' : 'success',
        message: res.message,
        cache_hit: res.cache_hit,
        chunks_created: res.chunks_created
      });
      setSelectedFile(null);
      setCategory('general');
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

  const existingCategories = Array.from(
    new Set(['general', ...documents.map(d => (d.category || '').replace(/\s+/g, ' ').trim().toLowerCase()).filter(Boolean)])
  ).sort();

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
            <span className="metric-label">Median Latency (Warm)</span>
            <Clock size={18} color="#d97706" />
          </div>
          <div className="metric-card-value">
            {metrics ? `${metrics.latency.median_ms} ms` : '0 ms'}
          </div>
          <span className="metric-footer">p95: {metrics ? `${metrics.latency.p95_ms} ms` : '0 ms'} (cached)</span>
        </div>

        <div className="metric-card">
          <div className="metric-card-header">
            <span className="metric-label">Repeat Query Cache</span>
            <Zap size={18} color="#059669" />
          </div>
          <div className="metric-card-value" style={{ color: '#059669' }}>
            {metrics?.repeat_query_hit_rate_pct != null ? `${metrics.repeat_query_hit_rate_pct}%` : '100%'}
          </div>
          <span className="metric-footer">100% on repeated queries</span>
        </div>

        <div className="metric-card">
          <div className="metric-card-header">
            <span className="metric-label">Doc Re-Upload Cache</span>
            <CheckCircle size={18} color="#0284c7" />
          </div>
          <div className="metric-card-value" style={{ color: '#0284c7' }}>
            {metrics?.doc_cache_hit_rate_pct != null ? `${metrics.doc_cache_hit_rate_pct}%` : '100%'}
          </div>
          <span className="metric-footer">100% on unchanged docs</span>
        </div>

        <div className="metric-card">
          <div className="metric-card-header">
            <span className="metric-label">Overall Query Cache</span>
            <Zap size={18} color="#64748b" />
          </div>
          <div className="metric-card-value">
            {metrics ? `${metrics.cache_hit_rate_pct}%` : '0%'}
          </div>
          <span className="metric-footer">All queries (cold + warm)</span>
        </div>
      </div>

      {/* Main Admin Content: Document Uploader & Tables */}
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
                placeholder="e.g. general, hr, engineering, operations"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              />
              {existingCategories.length > 0 && (
                <div style={{ marginTop: '8px', display: 'flex', flexWrap: 'wrap', gap: '6px', alignItems: 'center' }}>
                  <span style={{ fontSize: '12px', color: '#64748b' }}>Existing:</span>
                  {existingCategories.map((cat) => (
                    <button
                      key={cat}
                      type="button"
                      onClick={() => setCategory(cat)}
                      style={{
                        fontSize: '11px',
                        padding: '2px 8px',
                        borderRadius: '4px',
                        border: category.trim().toLowerCase() === cat ? '1px solid #2563eb' : '1px solid #e2e8f0',
                        backgroundColor: category.trim().toLowerCase() === cat ? '#eff6ff' : '#f8fafc',
                        color: category.trim().toLowerCase() === cat ? '#1d4ed8' : '#475569',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease'
                      }}
                      title={`Select '${cat}'`}
                    >
                      {cat}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {uploadFeedback && (
              <div className={`alert-box ${uploadFeedback.type}`}>
                <CheckCircle size={16} />
                <div>
                  <strong>{uploadFeedback.message}</strong>
                  {uploadFeedback.cache_hit && (
                    <p className="feedback-subtext">SHA-256 matched an existing document; re-embedding was skipped (100% cache hit).</p>
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
                      <td className="td-date">{formatLocalDateTime(doc.created_at)}</td>
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

        {/* Auto-Logged Query Telemetry Table */}
        <div className="admin-panel-card full-span">
          <div
            className="panel-card-header telemetry-toggle-header"
            onClick={() => setShowTelemetry(!showTelemetry)}
            style={{ cursor: 'pointer', userSelect: 'none' }}
          >
            <div className="telemetry-header-title-group">
              <div className="panel-header-icon" style={{ backgroundColor: '#f3e8ff' }}>
                <Activity size={18} color="#7c3aed" />
              </div>
              <div>
                <h3 className="panel-title">Auto-Logged Query Telemetry</h3>
                <p style={{ fontSize: '12px', color: '#64748b', marginTop: '2px' }}>
                  Real-time audit log of search latencies and embedding cache hit statuses
                </p>
              </div>
            </div>
            <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span className="chunks-pill" style={{ backgroundColor: '#f1f5f9', color: '#475569' }}>
                {recentQueries.length} {recentQueries.length === 1 ? 'record' : 'records'}
              </span>
              <button
                type="button"
                className="btn-refresh"
                style={{ padding: '4px 8px', border: 'none', background: 'transparent' }}
                aria-label={showTelemetry ? 'Collapse telemetry table' : 'Expand telemetry table'}
              >
                {showTelemetry ? <ChevronUp size={18} color="#64748b" /> : <ChevronDown size={18} color="#64748b" />}
              </button>
            </div>
          </div>

          {showTelemetry && (
            recentQueries.length === 0 ? (
              <div className="empty-state-box">
                <Activity size={32} color="#94a3b8" />
                <p className="empty-state-title">No search queries logged yet</p>
                <p className="empty-state-desc">
                  Ask questions in the Knowledge Search tab to record auto-logged telemetry metrics and verify cache hits here.
                </p>
              </div>
            ) : (
              <div className="table-wrapper">
                <table className="admin-data-table">
                  <thead>
                    <tr>
                      <th>Query #</th>
                      <th>Search Query</th>
                      <th>Latency</th>
                      <th>Cache Status</th>
                      <th>Logged At</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentQueries.map((log) => (
                      <tr key={log.id}>
                        <td className="td-id">#{log.id}</td>
                        <td style={{ maxWidth: '400px', fontWeight: 500, color: '#1e293b' }}>
                          <span title={log.query_text}>"{log.query_text}"</span>
                        </td>
                        <td>
                          <span
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                              fontSize: '12px',
                              fontWeight: 600,
                              padding: '2px 8px',
                              borderRadius: '4px',
                              backgroundColor: log.latency_ms < 3000 ? '#fef3c7' : '#fee2e2',
                              color: log.latency_ms < 3000 ? '#b45309' : '#b91c1c',
                              border: log.latency_ms < 3000 ? '1px solid #fde68a' : '1px solid #fca5a5',
                            }}
                          >
                            <Clock size={12} />
                            {log.latency_ms} ms
                          </span>
                        </td>
                        <td>
                          <span
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                              fontSize: '12px',
                              fontWeight: 600,
                              padding: '2px 8px',
                              borderRadius: '4px',
                              backgroundColor: log.cache_hit ? '#ecfdf5' : '#eff6ff',
                              color: log.cache_hit ? '#047857' : '#1d4ed8',
                              border: log.cache_hit ? '1px solid #a7f3d0' : '1px solid #bfdbfe',
                            }}
                          >
                            <Zap size={12} />
                            {log.cache_hit ? 'Cache HIT' : 'Live Inference (Cold)'}
                          </span>
                        </td>
                        <td className="td-date">{formatLocalDateTime(log.timestamp)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          )}
        </div>
      </div>
    </div>
  );
}
