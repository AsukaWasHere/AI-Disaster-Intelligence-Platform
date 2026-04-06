import React, { useState, useEffect, useCallback } from 'react'
import { fetchInsights } from '../services/api'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorBanner from '../components/ErrorBanner'

// ─── Helpers ────────────────────────────────────────────────────────────────

function formatDamage(value) {
  if (value == null) return '—'
  if (value >= 1_000_000_000) return `$${(value / 1_000_000_000).toFixed(1)}B`
  if (value >= 1_000_000)     return `$${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000)         return `$${(value / 1_000).toFixed(0)}K`
  return `$${value}`
}

function formatEvents(value) {
  if (value == null) return '—'
  return value.toLocaleString()
}

function stateCode(name = '') {
  const map = {
    California: 'CA', Florida: 'FL', Texas: 'TX', 'New York': 'NY',
    Japan: 'JP', Kanto: 'JP', India: 'IN', Australia: 'AU',
  }
  for (const [k, v] of Object.entries(map)) {
    if (name.includes(k)) return v
  }
  return name.slice(0, 2).toUpperCase()
}

function deriveHazard(name = '') {
  const n = name.toLowerCase()
  if (n.includes('japan') || n.includes('kanto') || n.includes('seismic'))
    return { label: 'Seismic', color: '#a855f7' }
  if (n.includes('florida') || n.includes('hurricane') || n.includes('atlantic'))
    return { label: 'Hurricane', color: '#00e5ff' }
  if (n.includes('fire') || n.includes('california'))
    return { label: 'Wildfire', color: '#ff4444' }
  return { label: 'Hazard', color: '#f59e0b' }
}

function scoreBarColor(score) {
  if (score >= 80) return 'linear-gradient(90deg,#ff4444,#ff6b35)'
  if (score >= 60) return 'linear-gradient(90deg,#00e5ff,#00ffa3)'
  return 'linear-gradient(90deg,#a855f7,#6366f1)'
}

// ─── Sub-components ─────────────────────────────────────────────────────────

const MetricCard = ({ icon, iconBg, title, value, valueColor, badgeValue, badgeColor, subtitle, loading }) => (
  <div className="metric-card rounded-xl p-5 flex-1 min-w-0">
    <div className="flex items-start justify-between mb-3">
      <div className="text-xs text-slate-500 font-medium">{title}</div>
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-lg ${iconBg}`}>
        {icon}
      </div>
    </div>

    {loading ? (
      <div className="h-9 w-24 rounded-lg bg-slate-800 animate-pulse mb-2" />
    ) : (
      <div className="text-3xl font-bold tracking-tight mb-2" style={{ color: valueColor }}>
        {value}
      </div>
    )}

    <div className="flex items-center gap-1.5">
      {loading ? (
        <div className="h-3 w-32 rounded bg-slate-800 animate-pulse" />
      ) : (
        <>
          <span className="text-xs font-semibold" style={{ color: badgeColor }}>↗ {badgeValue}</span>
          <span className="text-xs text-slate-500">{subtitle}</span>
        </>
      )}
    </div>
  </div>
)

const RiskRow = ({ code, region, hazard, hazardColor, score }) => {
  const barColor   = scoreBarColor(score)
  const scoreColor = score >= 80 ? '#ff4444' : score >= 60 ? '#00e5ff' : '#a855f7'
  const trendIcon  = score >= 80 ? '↗' : score >= 60 ? '→' : '↘'
  const trendColor = score >= 80 ? '#ff4444' : score >= 60 ? '#94a3b8' : '#00ffa3'

  return (
    <div className="flex items-center py-4 border-b border-sborder last:border-0 hover:bg-white/[0.02] transition-colors rounded-lg px-2 -mx-2">
      <div className="w-32 flex items-center gap-2.5">
        <div className="w-8 h-8 rounded-lg bg-ssurface border border-sborder flex items-center justify-center text-[10px] font-bold text-slate-400">
          {code}
        </div>
        <span className="text-sm text-slate-300 font-medium leading-tight">{region}</span>
      </div>
      <div className="w-28 flex items-center gap-1.5">
        <span className="w-1.5 h-1.5 rounded-full" style={{ background: hazardColor }} />
        <span className="text-xs font-medium" style={{ color: hazardColor }}>{hazard}</span>
      </div>
      <div className="flex-1 flex items-center gap-3">
        <div className="flex-1 max-w-24 h-1 rounded-full bg-slate-800 overflow-hidden">
          <div className="h-full rounded-full" style={{ width: `${Math.min(score, 100)}%`, background: barColor }} />
        </div>
        <span className="text-sm font-bold w-6" style={{ color: scoreColor }}>{score}</span>
      </div>
      <div className="w-16 flex justify-center">
        <span className="text-lg" style={{ color: trendColor }}>{trendIcon}</span>
      </div>
      <div className="w-20 flex justify-end">
        <button className="text-xs font-semibold hover:underline" style={{ color: '#00e5ff' }}>Deep Dive</button>
      </div>
    </div>
  )
}

const SkeletonRow = () => (
  <div className="flex items-center py-4 border-b border-sborder gap-4 px-2">
    <div className="w-32 flex items-center gap-2.5">
      <div className="w-8 h-8 rounded-lg bg-slate-800 animate-pulse" />
      <div className="h-3 w-20 rounded bg-slate-800 animate-pulse" />
    </div>
    <div className="w-28 h-3 rounded bg-slate-800 animate-pulse" />
    <div className="flex-1 h-1 rounded bg-slate-800 animate-pulse" />
    <div className="w-16 h-3 rounded bg-slate-800 animate-pulse" />
    <div className="w-20 h-3 rounded bg-slate-800 animate-pulse" />
  </div>
)

// ─── Page ────────────────────────────────────────────────────────────────────

export default function OverviewPage() {
  const [activeTab, setActiveTab] = useState('Active Zones')
  const [insights, setInsights]   = useState(null)
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchInsights()
      setInsights(data)
    } catch (err) {
      setError(err.message || 'Failed to fetch insights.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const totalEvents = insights ? formatEvents(insights.total_events)        : '—'
  const avgDamage   = insights ? formatDamage(insights.avg_damage_usd)      : '—'
  const avgRisk     = insights ? insights.avg_risk_score?.toFixed(1)        : '—'
  const highRisk    = insights?.high_risk_states ?? []

  return (
    <div className="p-6 max-w-screen-xl">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-white tracking-tight">System Overview</h1>
        <p className="text-slate-500 text-sm mt-1">Real-time intelligence feed and disaster impact forecasting.</p>
      </div>

      {error && (
        <div className="mb-5">
          <ErrorBanner message={error} onRetry={load} />
        </div>
      )}

      {/* Metrics Row */}
      <div className="flex gap-4 mb-6">
        <MetricCard
          icon="▲" iconBg="bg-teal-900/50"
          title="Total Events (24h)" value={totalEvents} valueColor="#00e5ff"
          badgeValue="12%" badgeColor="#00ffa3" subtitle="vs previous period" loading={loading}
        />
        <MetricCard
          icon="$" iconBg="bg-blue-900/50"
          title="Avg Damage Est." value={avgDamage} valueColor="#00e5ff"
          badgeValue="4%" badgeColor="#ff6b35" subtitle="Risk escalation noted" loading={loading}
        />
        <MetricCard
          icon="⊞" iconBg="bg-purple-900/50"
          title="Avg Risk Score" value={avgRisk} valueColor="#a855f7"
          badgeValue="2.1" badgeColor="#00ffa3" subtitle="System stabilization active" loading={loading}
        />
      </div>

      {/* Main Content Row */}
      <div className="flex gap-4">
        {/* High-Risk Regional Analysis */}
        <div className="flex-1 bg-scard border border-sborder rounded-xl p-5">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-base font-bold text-white">High-Risk Regional Analysis</h2>
            <div className="flex gap-1.5">
              {['Global', 'Active Zones'].map(tab => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                    activeTab === tab ? 'bg-ssurface text-white border' : 'text-slate-500 hover:text-slate-300'
                  }`}
                  style={activeTab === tab ? { borderColor: 'rgba(0,229,255,0.4)' } : {}}
                >
                  {tab}
                </button>
              ))}
            </div>
          </div>

          {/* Table header */}
          <div className="flex items-center px-2 mb-1">
            {['State / Territory','Primary Hazard','Risk Score','Trend','Actions'].map((h, i) => (
              <div
                key={h}
                className={`text-[10px] font-semibold text-slate-600 uppercase tracking-widest ${
                  i === 0 ? 'w-32' : i === 1 ? 'w-28' : i === 2 ? 'flex-1' : i === 3 ? 'w-16 text-center' : 'w-20 text-right'
                }`}
              >
                {h}
              </div>
            ))}
          </div>

          {loading ? (
            <><SkeletonRow /><SkeletonRow /><SkeletonRow /></>
          ) : highRisk.length > 0 ? (
            highRisk.map((region, i) => {
              const { label, color } = deriveHazard(region)
              const score = Math.max(45, 92 - i * 15)
              return (
                <RiskRow
                  key={region}
                  code={stateCode(region)}
                  region={region}
                  hazard={label}
                  hazardColor={color}
                  score={score}
                />
              )
            })
          ) : (
            /* Graceful fallback if API returns no high_risk_states */
            <>
              <RiskRow code="CA" region="California, USA" hazard="Wildfire"  hazardColor="#ff4444" score={92} />
              <RiskRow code="FL" region="Florida, USA"    hazard="Hurricane" hazardColor="#00e5ff" score={74} />
              <RiskRow code="JP" region="Kanto, Japan"    hazard="Seismic"   hazardColor="#a855f7" score={61} />
            </>
          )}

          <div className="mt-4 text-center">
            <button className="text-[11px] font-semibold text-slate-500 hover:text-slate-300 uppercase tracking-widest transition-colors">
              View Full Global Matrix
            </button>
          </div>
        </div>

        {/* Right Panel */}
        <div className="w-72 flex flex-col gap-4">
          {/* Neural Insights */}
          <div className="bg-scard border border-sborder rounded-xl p-4">
            <div className="flex items-center gap-2.5 mb-4">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: 'rgba(168,85,247,0.2)' }}>
                <span className="text-base">🤖</span>
              </div>
              <span className="text-sm font-bold text-white">Neural Insights</span>
            </div>

            <div className="space-y-3">
              <div className="insight-card rounded-lg p-3">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[9px] font-bold uppercase tracking-widest" style={{ color: '#00e5ff' }}>Satellite Anomaly</span>
                  <span className="text-[10px] text-slate-600">2m ago</span>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Thermal fluctuations detected in Northern California sector 4B. Risk score adjusted +5.2%.
                </p>
              </div>
              <div className="insight-card rounded-lg p-3">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[9px] font-bold uppercase tracking-widest" style={{ color: '#a855f7' }}>Atmospheric Model</span>
                  <span className="text-[10px] text-slate-600">14m ago</span>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Pacific high-pressure system shifting south. Probable hurricane dissipation in Atlantic Corridor.
                </p>
              </div>
            </div>

            <button className="btn-action w-full mt-4 py-2.5 rounded-lg text-xs font-bold uppercase tracking-widest">
              Generate Action Plan
            </button>
          </div>

          {/* Live Geospatial Feed */}
          <div className="bg-scard border border-sborder rounded-xl overflow-hidden">
            <div className="relative h-36 bg-slate-900">
              <div className="absolute inset-0 flex items-center justify-center">
                <svg viewBox="0 0 400 200" className="w-full h-full opacity-60">
                  <defs>
                    <radialGradient id="mapGlow" cx="50%" cy="50%" r="50%">
                      <stop offset="0%" stopColor="#00e5ff" stopOpacity="0.1"/>
                      <stop offset="100%" stopColor="transparent"/>
                    </radialGradient>
                  </defs>
                  <rect width="400" height="200" fill="#0a1628"/>
                  <path d="M60 60 L100 50 L130 55 L140 80 L120 100 L90 95 L60 80Z" fill="#1a3a2a" stroke="#2d5a3d" strokeWidth="0.5"/>
                  <path d="M160 40 L220 35 L250 50 L260 75 L240 90 L210 85 L175 80 L155 60Z" fill="#1a3a2a" stroke="#2d5a3d" strokeWidth="0.5"/>
                  <path d="M270 50 L320 45 L340 65 L330 85 L300 90 L270 75Z" fill="#1a3a2a" stroke="#2d5a3d" strokeWidth="0.5"/>
                  <path d="M170 100 L200 95 L210 120 L195 140 L175 130 L165 110Z" fill="#1a3a2a" stroke="#2d5a3d" strokeWidth="0.5"/>
                  <path d="M280 70 L310 65 L320 90 L305 110 L285 105 L275 85Z" fill="#1a3a2a" stroke="#2d5a3d" strokeWidth="0.5"/>
                  <circle cx="120" cy="75" r="4" fill="#ff4444" opacity="0.8">
                    <animate attributeName="r" values="4;7;4" dur="2s" repeatCount="indefinite"/>
                    <animate attributeName="opacity" values="0.8;0.3;0.8" dur="2s" repeatCount="indefinite"/>
                  </circle>
                  <circle cx="195" cy="65" r="3" fill="#00e5ff" opacity="0.6">
                    <animate attributeName="r" values="3;5;3" dur="2.5s" repeatCount="indefinite"/>
                  </circle>
                  <circle cx="305" cy="78" r="3" fill="#a855f7" opacity="0.6">
                    <animate attributeName="r" values="3;5;3" dur="3s" repeatCount="indefinite"/>
                  </circle>
                </svg>
              </div>
            </div>
            <div className="p-3 border-t border-sborder flex items-center justify-between">
              <div>
                <div className="text-xs font-semibold text-white">Live Geospatial Feed</div>
                <div className="text-[10px] text-slate-500 mt-0.5">
                  {loading ? 'Connecting...' : `${highRisk.length || 3} active monitoring satellites`}
                </div>
              </div>
              <div className="live-dot" />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
