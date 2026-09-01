import React, { useState, useEffect, useRef } from 'react';
import { searchService, documentService } from '../api/client';
import SourceCard from '../components/SourceCard';
import MetricsBadge from '../components/MetricsBadge';
import { Search, Send, Sparkles, Filter, Trash2, HelpCircle, FileQuestion, ArrowRight } from 'lucide-react';

const SUGGESTED_QUERIES = [
  "What is the Paid Time Off (PTO) policy?",
  "How many consecutive days of sick leave can I take without a note?",
  "What is the procedure for working remotely?",
  "How do I submit an expense reimbursement request?"
];

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [availableCategories, setAvailableCategories] = useState(['general']);
  const [history, setHistory] = useState([]); // List of { query, answer, standalone_query, sources, metrics, role }
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const chatEndRef = useRef(null);

  // Fetch distinct categories from ingested documents on mount
  useEffect(() => {
    async function loadCategories() {
      try {
        const docs = await documentService.getDocuments();
        const cats = Array.from(
          new Set(['general', ...docs.map(d => (d.category || '').replace(/\s+/g, ' ').trim().toLowerCase()).filter(Boolean)])
        ).sort();
        if (cats.length > 0) {
          setAvailableCategories(cats);
        }
      } catch {
        // Fallback to default general
      }
    }
    loadCategories();
  }, []);

  // Scroll to bottom of chat when new message is added
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [history, loading]);

  const handleSearch = async (e, customQuery = null) => {
    if (e) e.preventDefault();
    const searchQuery = (customQuery || query).trim();
    if (!searchQuery || loading) return;

    setError('');
    setLoading(true);

    // Build chat history payload for follow-up query reformulation
    const historyPayload = history.flatMap(item => [
      { role: 'user', content: item.query },
      { role: 'assistant', content: item.answer }
    ]);

    try {
      const result = await searchService.search(
        searchQuery,
        categoryFilter || null,
        historyPayload
      );

      setHistory(prev => [
        ...prev,
        {
          id: Date.now(),
          query: result.query,
          standalone_query: result.standalone_query,
          answer: result.answer,
          sources: result.sources || [],
          metrics: result.metrics || null,
          category_filter: categoryFilter || null,
        }
      ]);
      setQuery('');
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Search operation failed';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleClearHistory = () => {
    setHistory([]);
    setError('');
  };

  return (
    <div className="search-page-container">
      {/* Top Header & Search Controls */}
      <div className="search-header-panel">
        <div className="search-title-area">
          <h1 className="search-main-title">Guidely Knowledge Search</h1>
          <p className="search-main-desc">
            Ask any policy, workflow, or operational question grounded in company documentation.
          </p>
        </div>

        {/* Search Bar Form */}
        <form onSubmit={(e) => handleSearch(e)} className="search-input-form">
          <div className="search-box-wrapper">
            <div className="search-input-group">
              <Search size={18} className="search-icon" />
              <input
                type="text"
                className="search-input"
                placeholder="Ask a question (e.g. How many PTO days do full-time employees get?)..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                disabled={loading}
              />
            </div>

            {/* Category Filter Selector */}
            <div className="category-filter-group">
              <Filter size={15} className="filter-icon" />
              <select
                className="category-select"
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
              >
                <option value="">All Categories</option>
                {availableCategories.map(cat => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </select>
            </div>

            <button
              type="submit"
              className="btn-search-submit"
              disabled={loading || !query.trim()}
            >
              {loading ? (
                <div className="spinner-small" />
              ) : (
                <>
                  <span>Search</span>
                  <Send size={15} />
                </>
              )}
            </button>
          </div>
        </form>

        {/* Starter Suggestion Pills (Shown when no chat history) */}
        {history.length === 0 && (
          <div className="suggested-queries-section">
            <span className="suggested-label">
              <Sparkles size={14} color="#2563eb" />
              Try asking:
            </span>
            <div className="suggested-pills-list">
              {SUGGESTED_QUERIES.map((q, idx) => (
                <button
                  key={idx}
                  type="button"
                  className="suggested-pill"
                  onClick={() => handleSearch(null, q)}
                >
                  <span>{q}</span>
                  <ArrowRight size={12} />
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Error Alert */}
      {error && (
        <div className="alert-box error">
          <FileQuestion size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* Conversation Thread / Results List */}
      <div className="search-results-thread">
        {history.length > 0 && (
          <div className="thread-actions-bar">
            <span className="thread-count">{history.length} {history.length === 1 ? 'Query' : 'Queries'} in thread</span>
            <button className="btn-clear-thread" onClick={handleClearHistory}>
              <Trash2 size={14} />
              <span>Clear History</span>
            </button>
          </div>
        )}

        {history.map((item) => (
          <div key={item.id} className="search-turn-card">
            {/* User Question */}
            <div className="turn-question-box">
              <div className="user-avatar-tag">User</div>
              <div className="question-content">
                <p className="question-text">{item.query}</p>
                {item.standalone_query && item.standalone_query !== item.query && (
                  <div className="standalone-query-hint" title="Conversational query reformulated by Gemini">
                    <Sparkles size={12} />
                    <span>Contextualized: <em>"{item.standalone_query}"</em></span>
                  </div>
                )}
              </div>
            </div>

            {/* AI Generated Answer */}
            <div className="turn-answer-box">
              <div className="assistant-header">
                <div className="assistant-avatar-tag">
                  <Sparkles size={13} />
                  <span>Guidely Answer</span>
                </div>
                {item.metrics && <MetricsBadge metrics={item.metrics} />}
              </div>

              <div className="answer-body">
                <p className="answer-text">{item.answer}</p>
              </div>

              {/* Source Snippets Citations */}
              {item.sources && item.sources.length > 0 && (
                <div className="turn-sources-section">
                  <h4 className="sources-heading">
                    <span>Cited Sources ({item.sources.length})</span>
                  </h4>
                  <div className="sources-grid">
                    {item.sources.map((source, sIdx) => (
                      <SourceCard key={sIdx} source={source} index={sIdx} />
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Loading Indicator for In-Flight Search */}
        {loading && (
          <div className="search-loading-card">
            <div className="loading-spinner-ring" />
            <div className="loading-text-group">
              <p className="loading-title">Retrieving context & generating answer...</p>
              <p className="loading-subtitle">Querying FAISS vector index & synthesizing with Gemini</p>
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>
    </div>
  );
}
