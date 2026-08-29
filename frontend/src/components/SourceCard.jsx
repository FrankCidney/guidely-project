import React, { useState } from 'react';
import { FileText, ChevronDown, ChevronUp, Tag, Percent } from 'lucide-react';

export default function SourceCard({ source, index }) {
  const [expanded, setExpanded] = useState(false);

  // Confidence percentage from similarity score (e.g. 0.884 -> 88.4%)
  const scorePercent = source.similarity_score
    ? Math.round(source.similarity_score * 100)
    : null;

  return (
    <div className="source-card">
      <div className="source-card-header" onClick={() => setExpanded(!expanded)}>
        <div className="source-card-title-group">
          <FileText size={16} className="source-icon" />
          <span className="source-filename">{source.file_name}</span>
          {source.category && (
            <span className="source-category-tag">
              <Tag size={11} />
              {source.category}
            </span>
          )}
        </div>

        <div className="source-card-meta">
          {scorePercent !== null && (
            <span className="score-badge" title="Vector Match Confidence">
              <Percent size={11} />
              {scorePercent}% match
            </span>
          )}
          <button className="btn-toggle-snippet" aria-label="Toggle snippet">
            {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
        </div>
      </div>

      <div className={`source-snippet-container ${expanded ? 'expanded' : 'collapsed'}`}>
        <p className="source-snippet-text">{source.snippet}</p>
      </div>
    </div>
  );
}
