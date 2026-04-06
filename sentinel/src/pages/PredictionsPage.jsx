import React, { useState } from 'react'
import { runPrediction } from '../services/api'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorBanner from '../components/ErrorBanner'

// ─── Helpers ────────────────────────────────────────────────────────────────

const MONTHS = [
  'January','February','March','April','May','June',
  'July','August','September','October','November','December',
]

/** Map month name → 1-based number for the API */
const monthToNum = (name) => MONTHS.indexOf(name) + 1

/** Format a raw USD damage number */
function formatDamage(value) {
  if (value == null) return '—'
  if (value >= 1_000_000_000) return `$${(value / 1_000_000_000).toFixed(1)}B`
  if (value >= 1_000_000)     return `$${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000)         return `$${(value / 1_000).toFixed(0)}K`
  return `$${value}`
}

/** Choose a bar gradient based on position in the list */
const BAR_CLASSES = [
  '',                          // default cyan
  'probability-fill-purple',
  'probability-fill-orange',
]

/** Map event type label to an emoji icon */
function eventIcon(label = '') {
  const l = label.toLowerCase()
  if (l.includes('earthquake') || l.includes('seismic')) return '🌍'
  if (l.includes('tsunami'))                              return '🌊'
  if (l.includes('hurricane') || l.includes('typhoon'))  return '🌀'
  if (l.includes('flood'))                               return '💧'
  if (l.includes('fire') || l.includes('wildfire'))      return '🔥'
  if (l.includes('landslide'))                           return '🏔️'
  if (l.includes('tornado'))                             return '🌪️'
  return '⚡'
}

/** Derive tag color palette by index */
function tagColor(i) {
  const palettes = [
    { bg: 'rgba(0,229,255,0.1)',   text: '#00e5ff', border: 'rgba(0,229,255,0.2)' },
    { bg: 'rgba(245,158,11,0.1)', text: '#f59e0b', border: 'rgba(245,158,11,0.2)' },
    { bg: 'rgba(239,68,68,0.1)',  text: '#ef4444', border: 'rgba(239,68,68,0.2)' },
    { bg: 'rgba(168,85,247,0.1)', text: '#a855f7', border: 'rgba(168,85,247,0.2)' },
  ]
  return palettes[i % palettes.length]
}

// ─── Sub-components ─────────────────────────────────────────────────────────

const PredictionCard = ({ icon, title, keywords, probability, barClass, description, index }) => {
  const tc = tagColor(index)
  return (
    <div className="bg-ssurface border border-sborder rounded-xl p-4 hover:border-slate-600 transition-colors">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-scard flex items-center justify-center text-xl">{icon}</div>
          <div>
            <div className="text-sm font-bold text-white mb-1">{title}</div>
            <div className="flex flex-wrap gap-1.5">
              {(keywords ?? []).slice(0, 2).map((kw, i) => (
                <span
                  key={kw}
                  className="tag"
                  style={{ background: tagColor(i).bg, color: tagColor(i).text, border: `1px solid ${tagColor(i).border}` }}
                >
                  {kw.toUpperCase()}
                </span>
              ))}
            </div>
          </div>
        </div>
        <span className="text-base font-bold text-white tabular-nums">
          {(probability * 100).toFixed(0)}%
        </span>
      </div>
      <div className="probability-bar my-3">
        <div
          className={`probability-fill ${barClass}`}
          style={{ width: `${Math.min((probability * 100).toFixed(0), 100)}%` }}
        />
      </div>
      {description && (
        <p className="text-xs text-slate-500 leading-relaxed">{description}</p>
      )}
    </div>
  )
}

/** Skeleton card for loading state */
const SkeletonPredictionCard = () => (
  <div className="bg-ssurface border border-sborder rounded-xl p-4">
    <div className="flex items-center gap-3 mb-3">
      <div className="w-10 h-10 rounded-xl bg-slate-800 animate-pulse" />
      <div className="flex-1 space-y-2">
        <div className="h-3 w-32 rounded bg-slate-800 animate-pulse" />
        <div className="h-2 w-20 rounded bg-slate-800 animate-pulse" />
      </div>
    </div>
    <div className="h-1 rounded bg-slate-800 animate-pulse my-3" />
    <div className="h-2 w-full rounded bg-slate-800 animate-pulse" />
  </div>
)

// ─── Page ────────────────────────────────────────────────────────────────────

export default function PredictionsPage() {
  const [magnitude, setMagnitude] = useState(7.2)
  const [form, setForm] = useState({
    latitude: '',
    longitude: '',
    month: '',
    narrative: '',
  })
  const [result, setResult]     = useState(null)
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState(null)

  const handleSubmit = async () => {
    // Basic validation
    if (!form.latitude || !form.longitude || !form.month) {
      setError('Please fill in Latitude, Longitude, and Month before running the prediction.')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const data = await runPrediction({
        lat:       parseFloat(form.latitude),
        lon:       parseFloat(form.longitude),
        month:     monthToNum(form.month),
        magnitude: magnitude,
        narrative: form.narrative,
      })
      setResult(data)
    } catch (err) {
      setError(err.message || 'Prediction failed. Please check the backend and try again.')
    } finally {
      setLoading(false)
    }
  }

  // ── Derived display values from result ──────────────────────────────────
  const primaryThreat   = result?.event_type     ?? null
  const riskScore       = result?.risk_score      ?? null
  const damageUsd       = result?.damage_usd      ?? null
  const explanation     = result?.explanation     ?? null
  const topPredictions  = result?.top_predictions ?? []
  const keywords        = result?.keywords        ?? []

  return (
    <div className="p-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-xs text-slate-600 mb-4">
        <span className="uppercase tracking-widest">Intelligence</span>
        <span>›</span>
        <span className="uppercase tracking-widest font-semibold" style={{ color: '#00e5ff' }}>
          Predictive Modeling
        </span>
      </div>
      <h1 className="text-2xl font-bold text-white mb-6 tracking-tight">Disaster Risk Analysis</h1>

      <div className="flex gap-5">
        {/* ── Left: Parameters form ───────────────────────────────────────── */}
        <div className="w-80 flex-shrink-0 space-y-5">
          <div className="bg-scard border border-sborder rounded-xl p-5">
            <div className="flex items-center gap-2 mb-5">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#00e5ff" strokeWidth="2">
                <line x1="4" y1="6" x2="20" y2="6"/>
                <line x1="8" y1="12" x2="20" y2="12"/>
                <line x1="12" y1="18" x2="20" y2="18"/>
              </svg>
              <span className="text-sm font-bold text-white">Parameters</span>
            </div>

            {/* Lat / Long */}
            <div className="flex gap-3 mb-4">
              <div className="flex-1">
                <label className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 block mb-1.5">
                  Latitude
                </label>
                <input
                  className="form-input w-full rounded-lg px-3 py-2 text-sm"
                  placeholder="0.0000"
                  value={form.latitude}
                  onChange={e => setForm(p => ({ ...p, latitude: e.target.value }))}
                />
              </div>
              <div className="flex-1">
                <label className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 block mb-1.5">
                  Longitude
                </label>
                <input
                  className="form-input w-full rounded-lg px-3 py-2 text-sm"
                  placeholder="0.0000"
                  value={form.longitude}
                  onChange={e => setForm(p => ({ ...p, longitude: e.target.value }))}
                />
              </div>
            </div>

            {/* Month */}
            <div className="mb-4">
              <label className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 block mb-1.5">
                Temporal Window (Month)
              </label>
              <select
                className="form-input w-full rounded-lg px-3 py-2 text-sm appearance-none"
                value={form.month}
                onChange={e => setForm(p => ({ ...p, month: e.target.value }))}
              >
                <option value="">Select Month</option>
                {MONTHS.map(m => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>

            {/* Magnitude Slider */}
            <div className="mb-4">
              <div className="flex items-center justify-between mb-2">
                <label className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">
                  Historical Magnitude Reference
                </label>
                <span className="text-sm font-bold font-mono" style={{ color: '#00e5ff' }}>
                  {magnitude} Mw
                </span>
              </div>
              <input
                type="range" min="0" max="10" step="0.1"
                value={magnitude}
                onChange={e => setMagnitude(parseFloat(e.target.value))}
                className="w-full h-1 rounded-full appearance-none cursor-pointer"
                style={{
                  background: `linear-gradient(90deg, #00e5ff ${magnitude * 10}%, #1a2d4a ${magnitude * 10}%)`,
                }}
              />
              <div className="flex justify-between text-[10px] text-slate-600 mt-1">
                <span>0.0</span><span>5.0</span><span>10.0</span>
              </div>
            </div>

            {/* Narrative */}
            <div className="mb-5">
              <label className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 block mb-1.5">
                Scenario Narrative
              </label>
              <textarea
                className="form-input w-full rounded-lg px-3 py-2 text-sm resize-none h-24"
                placeholder="Describe specific environmental indicators or localized variables..."
                value={form.narrative}
                onChange={e => setForm(p => ({ ...p, narrative: e.target.value }))}
              />
            </div>

            {/* Validation error */}
            {error && !loading && (
              <div className="mb-4">
                <ErrorBanner message={error} onRetry={handleSubmit} />
              </div>
            )}

            <button
              className="btn-primary w-full py-3 rounded-xl text-sm uppercase tracking-widest flex items-center justify-center gap-2 disabled:opacity-60"
              onClick={handleSubmit}
              disabled={loading}
            >
              {loading ? (
                <>
                  <div
                    className="w-4 h-4 border-2 rounded-full animate-spin"
                    style={{ borderColor: 'rgba(8,13,26,0.3)', borderTopColor: '#080d1a' }}
                  />
                  Analyzing…
                </>
              ) : (
                'Run Prediction'
              )}
            </button>
          </div>

          {/* Scan Preview */}
          <div className="bg-scard border border-sborder rounded-xl overflow-hidden">
            <div className="relative h-44">
              <svg viewBox="0 0 320 176" className="w-full h-full">
                <defs>
                  <radialGradient id="scanGlow" cx="50%" cy="50%" r="50%">
                    <stop offset="0%" stopColor="#1a3a4a" stopOpacity="0.8"/>
                    <stop offset="100%" stopColor="#080d1a"/>
                  </radialGradient>
                </defs>
                <rect width="320" height="176" fill="url(#scanGlow)"/>
                <path d="M80 90 Q120 60 160 80 Q200 100 240 75"  fill="none" stroke="#1e3a5a" strokeWidth="1"/>
                <path d="M60 110 Q110 75 160 95 Q210 115 255 90" fill="none" stroke="#1e3a5a" strokeWidth="1"/>
                <path d="M70 130 Q115 95 160 110 Q210 130 260 105" fill="none" stroke="#1e3a5a" strokeWidth="1"/>
                <path d="M90 70 Q135 45 165 65 Q195 85 230 60"  fill="none" stroke="#243a5a" strokeWidth="1"/>
                <path d="M100 50 Q140 30 168 52 Q195 68 220 50" fill="none" stroke="#1a2d4a" strokeWidth="1"/>
                <ellipse cx="160" cy="88" rx="55" ry="40" fill="rgba(0,229,255,0.06)" stroke="rgba(0,229,255,0.12)" strokeWidth="1"/>
                <ellipse cx="160" cy="88" rx="30" ry="22" fill="rgba(0,229,255,0.08)" stroke="rgba(0,229,255,0.2)"  strokeWidth="1"/>
                {/* Scanning animation when loading */}
                {loading && (
                  <line x1="60" y1="88" x2="260" y2="88" stroke="#00e5ff" strokeWidth="1" strokeOpacity="0.6">
                    <animate attributeName="y1" values="40;136;40" dur="1.5s" repeatCount="indefinite"/>
                    <animate attributeName="y2" values="40;136;40" dur="1.5s" repeatCount="indefinite"/>
                    <animate attributeName="stroke-opacity" values="0.6;0.1;0.6" dur="1.5s" repeatCount="indefinite"/>
                  </line>
                )}
              </svg>
              <div className="absolute bottom-2 left-3 flex items-center gap-1.5">
                <div className={`w-1.5 h-1.5 rounded-full ${loading ? 'bg-yellow-400' : 'bg-green-400'}`} />
                <span className="text-[10px] text-slate-500 font-mono">
                  {form.latitude && form.longitude
                    ? `SCAN: ${parseFloat(form.latitude || 0).toFixed(4)}° N, ${parseFloat(form.longitude || 0).toFixed(4)}° E`
                    : 'ACTIVE SCAN AREA: 35.6895° N, 139.6917° E'
                  }
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* ── Right: Results panel ─────────────────────────────────────────── */}
        <div className="flex-1">
          {/* Loading state */}
          {loading && (
            <div className="bg-scard border border-sborder rounded-xl p-6 mb-4">
              <LoadingSpinner label="Running neural prediction…" />
            </div>
          )}

          {/* Error state (full panel) */}
          {error && !loading && !result && (
            <div className="bg-scard border border-sborder rounded-xl p-6">
              <ErrorBanner message={error} onRetry={handleSubmit} />
            </div>
          )}

          {/* Empty state — before first run */}
          {!loading && !result && !error && (
            <div className="bg-scard border border-sborder rounded-xl p-10 flex flex-col items-center justify-center text-center">
              <div className="text-4xl mb-4">🛰️</div>
              <div className="text-sm font-semibold text-slate-400 mb-1">No Analysis Yet</div>
              <div className="text-xs text-slate-600 max-w-xs">
                Fill in the parameters on the left and press <span style={{ color: '#00e5ff' }}>Run Prediction</span> to start a neural disaster risk analysis.
              </div>
            </div>
          )}

          {/* Results */}
          {result && !loading && (
            <div className="space-y-4">
              {/* Primary Threat card */}
              <div className="bg-scard border border-sborder rounded-xl p-6">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="text-[10px] font-bold uppercase tracking-widest mb-2" style={{ color: '#00e5ff' }}>
                      Primary Threat Detected
                    </div>
                    <h2 className="text-5xl font-bold text-white tracking-tight capitalize">
                      {primaryThreat}
                    </h2>

                    {/* Keywords */}
                    {keywords.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mt-3">
                        {keywords.map((kw, i) => {
                          const c = tagColor(i)
                          return (
                            <span
                              key={kw}
                              className="tag"
                              style={{ background: c.bg, color: c.text, border: `1px solid ${c.border}` }}
                            >
                              {kw.toUpperCase()}
                            </span>
                          )
                        })}
                      </div>
                    )}
                  </div>

                  <div className="text-right shrink-0 ml-4">
                    <div
                      className="w-16 h-16 rounded-xl border-2 flex items-center justify-center mb-1"
                      style={{
                        borderColor: riskScore >= 80 ? '#ff4444' : '#00e5ff',
                        background:  riskScore >= 80 ? 'rgba(255,68,68,0.08)' : 'rgba(0,229,255,0.08)',
                      }}
                    >
                      <span
                        className="text-2xl font-bold"
                        style={{ color: riskScore >= 80 ? '#ff4444' : '#00e5ff' }}
                      >
                        {riskScore}
                      </span>
                    </div>
                    <div className="text-[10px] text-slate-500 uppercase tracking-widest">Risk Score</div>
                  </div>
                </div>

                {/* Explanation */}
                {explanation && (
                  <p className="text-xs text-slate-400 leading-relaxed mt-4 border-t border-sborder pt-4">
                    {explanation}
                  </p>
                )}

                {/* Damage + confidence row */}
                <div className="flex gap-4 mt-5">
                  <div className="flex-1 bg-ssurface rounded-xl p-4 border border-sborder">
                    <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-2">
                      Projected Economic Impact
                    </div>
                    <div className="text-3xl font-bold text-white">{formatDamage(damageUsd)}</div>
                    <div className="flex items-center gap-1 mt-1">
                      <span className="text-xs font-semibold" style={{ color: '#ff6b35' }}>
                        ↗ Model-derived estimate
                      </span>
                    </div>
                  </div>
                  <div className="flex-1 bg-ssurface rounded-xl p-4 border border-sborder">
                    <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-2">
                      Top Prediction Confidence
                    </div>
                    <div className="text-3xl font-bold text-white">
                      {topPredictions[0]
                        ? `${(topPredictions[0].probability * 100).toFixed(1)}%`
                        : '—'
                      }
                    </div>
                    <div className="flex items-center gap-1.5 mt-1">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="#00ffa3">
                        <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                      </svg>
                      <span className="text-xs font-semibold" style={{ color: '#00ffa3' }}>High Reliability</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Alternative Probabilities */}
              {topPredictions.length > 0 && (
                <div>
                  <div className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-3">
                    Alternative Probabilities
                  </div>
                  <div className="space-y-3">
                    {topPredictions.map((pred, i) => (
                      <PredictionCard
                        key={pred.label}
                        index={i}
                        icon={eventIcon(pred.label)}
                        title={pred.label}
                        keywords={keywords.slice(i * 2, i * 2 + 2)}
                        probability={pred.probability}
                        barClass={BAR_CLASSES[i] ?? ''}
                        description={i === 0 ? explanation : null}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
