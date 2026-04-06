import React, { useState } from 'react'

const Toggle = ({ on, color = 'bg-scyan', onToggle }) => (
  <button
    onClick={onToggle}
    className={`w-10 h-5 rounded-full relative transition-colors duration-200 ${on ? (color === 'purple' ? 'bg-purple-500' : 'bg-cyan-400') : 'bg-slate-700'}`}
    style={on ? { background: color === 'purple' ? '#a855f7' : '#00e5ff' } : {}}
  >
    <div className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform duration-200 ${on ? 'translate-x-5' : 'translate-x-0.5'}`} />
  </button>
)

export default function GeospatialPage() {
  const [layers, setLayers] = useState({
    oceanic: true,
    tectonic: false,
    atmospheric: true,
  })
  const toggle = key => setLayers(p => ({ ...p, [key]: !p[key] }))

  return (
    <div className="relative h-full min-h-screen">
      {/* Full-width map background */}
      <div className="absolute inset-0 overflow-hidden">
        <svg viewBox="0 0 1200 800" className="w-full h-full">
          <defs>
            <radialGradient id="cityGlow" cx="50%" cy="60%" r="60%">
              <stop offset="0%" stopColor="#ff6b35" stopOpacity="0.25"/>
              <stop offset="60%" stopColor="#ff4444" stopOpacity="0.08"/>
              <stop offset="100%" stopColor="#080d1a" stopOpacity="0"/>
            </radialGradient>
          </defs>
          <rect width="1200" height="800" fill="#080d1a"/>
          <rect width="1200" height="800" fill="url(#cityGlow)"/>

          {/* City grid lines - urban area simulation */}
          {Array.from({ length: 30 }).map((_, i) => (
            <g key={`h${i}`}>
              <line x1="200" y1={100 + i * 22} x2="900" y2={100 + i * 22}
                stroke={`rgba(255,107,53,${Math.random() * 0.15 + 0.03})`} strokeWidth="0.5"/>
            </g>
          ))}
          {Array.from({ length: 25 }).map((_, i) => (
            <line key={`v${i}`} x1={200 + i * 28} y1="100" x2={200 + i * 28} y2="750"
              stroke={`rgba(255,107,53,${Math.random() * 0.12 + 0.03})`} strokeWidth="0.5"/>
          ))}

          {/* Diagonal roads */}
          <line x1="200" y1="200" x2="700" y2="700" stroke="rgba(255,140,60,0.2)" strokeWidth="1.5"/>
          <line x1="300" y1="150" x2="850" y2="650" stroke="rgba(255,120,50,0.15)" strokeWidth="1"/>
          <line x1="600" y1="100" x2="900" y2="700" stroke="rgba(255,100,40,0.18)" strokeWidth="1.5"/>

          {/* Bright intersections */}
          {[
            [400, 300], [500, 400], [350, 450], [600, 350], [450, 500], [550, 300], [650, 480]
          ].map(([x, y], i) => (
            <circle key={i} cx={x} cy={y} r={Math.random() * 3 + 1}
              fill={`rgba(255,${100 + Math.random() * 80},50,${Math.random() * 0.6 + 0.3})`}/>
          ))}

          {/* Active event dot */}
          <circle cx="680" cy="430" r="6" fill="#ff4444" opacity="0.9">
            <animate attributeName="r" values="6;12;6" dur="2s" repeatCount="indefinite"/>
            <animate attributeName="opacity" values="0.9;0.3;0.9" dur="2s" repeatCount="indefinite"/>
          </circle>
          <circle cx="680" cy="430" r="4" fill="#ff6b35"/>
        </svg>
      </div>

      {/* Active Layers Panel */}
      <div className="absolute top-4 left-4 w-64 bg-scard/95 border border-sborder rounded-xl p-4 backdrop-blur-sm z-10">
        <div className="flex items-center justify-between mb-4">
          <span className="text-sm font-bold text-white">Active Layers</span>
          <button className="text-slate-500 hover:text-white">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="4" y1="6" x2="20" y2="6"/><line x1="8" y1="12" x2="20" y2="12"/><line x1="12" y1="18" x2="20" y2="18"/>
            </svg>
          </button>
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <span className="text-base">🌊</span>
              <span className="text-sm text-slate-300">Oceanic Surge</span>
            </div>
            <Toggle on={layers.oceanic} onToggle={() => toggle('oceanic')} />
          </div>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <span className="text-base">🌋</span>
              <span className="text-sm text-slate-300">Tectonic Activity</span>
            </div>
            <Toggle on={layers.tectonic} onToggle={() => toggle('tectonic')} />
          </div>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <span className="text-base">🌪️</span>
              <span className="text-sm text-slate-300">Atmospheric Flux</span>
            </div>
            <Toggle on={layers.atmospheric} color="purple" onToggle={() => toggle('atmospheric')} />
          </div>
        </div>

        <button className="btn-action w-full mt-4 py-2 rounded-lg text-xs font-bold uppercase tracking-widest">
          Apply Simulation
        </button>
      </div>

      {/* Map Controls */}
      <div className="absolute top-4 right-4 flex flex-col gap-2 z-10">
        <button className="w-9 h-9 bg-scard/90 border border-sborder rounded-lg flex items-center justify-center text-slate-400 hover:text-white transition-colors backdrop-blur-sm">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="3"/><path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/>
          </svg>
        </button>
        <button className="w-9 h-9 bg-scard/90 border border-sborder rounded-lg flex items-center justify-center text-slate-400 hover:text-white transition-colors backdrop-blur-sm">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"/>
          </svg>
        </button>
        <button className="w-9 h-9 bg-scard/90 border border-sborder rounded-lg flex items-center justify-center text-slate-300 hover:text-white font-bold text-base transition-colors backdrop-blur-sm">+</button>
        <button className="w-9 h-9 bg-scard/90 border border-sborder rounded-lg flex items-center justify-center text-slate-300 hover:text-white font-bold text-base transition-colors backdrop-blur-sm">−</button>
      </div>

      {/* Bottom Stats */}
      <div className="absolute bottom-56 left-0 right-0 px-4 z-10">
        <div className="flex gap-3">
          <div className="geo-stat-card rounded-xl px-5 py-3">
            <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-1">Observation Area</div>
            <div className="text-xl font-bold" style={{ color: '#00e5ff' }}>4,820 <span className="text-xs text-slate-400 font-normal">km²</span></div>
          </div>
          <div className="geo-stat-card rounded-xl px-5 py-3">
            <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-1">Active Sensors</div>
            <div className="flex items-center gap-2">
              <span className="text-xl font-bold text-white">12,402</span>
              <div className="flex items-center gap-1">
                <div className="live-dot"></div>
                <span className="text-[10px] font-bold text-green-400 uppercase">LIVE</span>
              </div>
            </div>
          </div>
          <div className="geo-stat-card rounded-xl px-5 py-3">
            <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-1">Processing Latency</div>
            <div className="text-xl font-bold text-white">14 <span className="text-sm text-slate-400 font-normal">ms</span></div>
          </div>
          <div className="geo-stat-card rounded-xl px-5 py-3 border-red-900/50" style={{ borderColor: 'rgba(239,68,68,0.3)' }}>
            <div className="text-[10px] font-semibold uppercase tracking-widest mb-1" style={{ color: '#ff4444' }}>Current Threat</div>
            <div className="flex items-center gap-3">
              <span className="text-xl font-bold text-white">Extreme</span>
              <div className="w-12 h-12 rounded-xl border-2 flex items-center justify-center" style={{ borderColor: '#ff4444', background: 'rgba(255,68,68,0.1)' }}>
                <span className="text-base font-bold" style={{ color: '#ff4444' }}>92</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Sentinel Intel Card */}
      <div className="absolute bottom-4 right-4 w-80 bg-scard/95 border border-sborder rounded-xl p-4 backdrop-blur-sm z-10">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: 'rgba(168,85,247,0.2)' }}>
            <span className="text-base">🤖</span>
          </div>
          <div>
            <div className="text-sm font-bold text-white">Sentinel Intel</div>
            <div className="text-[10px] text-slate-500">Neural Analysis Engine</div>
          </div>
        </div>

        <p className="text-xs text-slate-400 leading-relaxed mb-3">
          Detected atmospheric pressure drop in{' '}
          <span style={{ color: '#00e5ff' }}>Sector 7-G</span>.
          Correlation with seismic markers suggests a 84% probability of localized subsidence.
        </p>

        <div className="flex gap-2">
          <button className="flex-1 py-2 rounded-lg bg-ssurface border border-sborder text-xs font-bold uppercase tracking-widest text-slate-300 hover:text-white transition-colors">
            Details
          </button>
          <button className="flex-1 py-2 rounded-lg text-xs font-bold uppercase tracking-widest transition-all hover:opacity-90"
            style={{ background: 'rgba(168,85,247,0.2)', border: '1px solid rgba(168,85,247,0.4)', color: '#a855f7' }}>
            Dispatch
          </button>
        </div>
      </div>
    </div>
  )
}
