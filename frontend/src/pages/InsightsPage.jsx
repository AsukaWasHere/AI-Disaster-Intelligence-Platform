import React from 'react'

export default function InsightsPage() {
  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold text-white mb-2">Insights</h1>
      <p className="text-slate-500 text-sm mb-8">Advanced neural analytics and pattern recognition.</p>
      <div className="grid grid-cols-2 gap-4">
        {['Pattern Recognition Engine', 'Anomaly Detection Matrix', 'Predictive Cascade Mapping', 'Historical Correlation Index'].map(title => (
          <div key={title} className="metric-card rounded-xl p-5">
            <div className="text-[10px] font-bold uppercase tracking-widest mb-3" style={{ color: '#00e5ff' }}>Module Active</div>
            <div className="text-base font-bold text-white mb-2">{title}</div>
            <div className="h-1 rounded-full bg-slate-800 overflow-hidden">
              <div className="h-full rounded-full" style={{
                width: `${Math.floor(Math.random() * 40 + 55)}%`,
                background: 'linear-gradient(90deg,#00e5ff,#a855f7)'
              }}></div>
            </div>
            <div className="text-[10px] text-slate-500 mt-1">Processing...</div>
          </div>
        ))}
      </div>
    </div>
  )
}
