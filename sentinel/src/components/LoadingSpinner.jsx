import React from 'react'

/**
 * Full-area centered loading spinner.
 * Pass size="sm" for inline/compact usage.
 */
export default function LoadingSpinner({ size = 'md', label = 'Loading...' }) {
  const dim = size === 'sm' ? 'w-5 h-5' : 'w-10 h-10'
  const border = size === 'sm' ? 'border-2' : 'border-[3px]'

  return (
    <div className="flex flex-col items-center justify-center gap-3 py-12">
      <div
        className={`${dim} ${border} rounded-full animate-spin`}
        style={{
          borderColor: 'rgba(0,229,255,0.15)',
          borderTopColor: '#00e5ff',
        }}
      />
      {size !== 'sm' && (
        <span className="text-xs text-slate-500 uppercase tracking-widest font-semibold animate-pulse">
          {label}
        </span>
      )}
    </div>
  )
}
