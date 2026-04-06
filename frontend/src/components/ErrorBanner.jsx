import React from 'react'

/**
 * Inline error banner.
 * onRetry — optional callback wired to a retry button.
 */
export default function ErrorBanner({ message, onRetry }) {
  return (
    <div
      className="flex items-start gap-3 rounded-xl border px-4 py-3 text-sm"
      style={{
        background: 'rgba(239,68,68,0.06)',
        borderColor: 'rgba(239,68,68,0.25)',
      }}
    >
      {/* Icon */}
      <svg
        className="mt-0.5 shrink-0"
        width="15"
        height="15"
        viewBox="0 0 24 24"
        fill="none"
        stroke="#ef4444"
        strokeWidth="2"
      >
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="8" x2="12" y2="12" />
        <line x1="12" y1="16" x2="12.01" y2="16" />
      </svg>

      <div className="flex-1">
        <span className="font-semibold" style={{ color: '#ef4444' }}>
          Error&nbsp;
        </span>
        <span className="text-slate-400">{message}</span>
      </div>

      {onRetry && (
        <button
          onClick={onRetry}
          className="shrink-0 text-xs font-bold uppercase tracking-widest transition-colors"
          style={{ color: '#00e5ff' }}
        >
          Retry
        </button>
      )}
    </div>
  )
}
