import React from 'react';
import { Zap, Clock, Layers } from 'lucide-react';

export default function MetricsBadge({ metrics }) {
  if (!metrics) return null;

  const { latency_ms, cache_hit, retrieved_chunks } = metrics;

  return (
    <div className="metrics-badge-container">
      <div className="metric-item latency" title="Total response latency">
        <Clock size={13} />
        <span>{latency_ms} ms</span>
      </div>

      <div
        className={`metric-item cache ${cache_hit ? 'hit' : 'miss'}`}
        title={cache_hit ? 'Response served from cache' : 'Fresh vector query & LLM run'}
      >
        <Zap size={13} />
        <span>{cache_hit ? 'Cache Hit' : 'Live Inference'}</span>
      </div>

      {typeof retrieved_chunks === 'number' && (
        <div className="metric-item chunks" title="Retrieved vector chunks">
          <Layers size={13} />
          <span>{retrieved_chunks} {retrieved_chunks === 1 ? 'chunk' : 'chunks'}</span>
        </div>
      )}
    </div>
  );
}
