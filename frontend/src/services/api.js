const BASE_URL = 'http://127.0.0.1:8000'

/**
 * Shared fetch wrapper with error handling.
 * Throws a structured error object on failure.
 */
async function request(path, options = {}) {
  const url = `${BASE_URL}${path}`
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })

  if (!res.ok) {
    let message = `Server error: ${res.status} ${res.statusText}`
    try {
      const body = await res.json()
      if (body?.detail) message = body.detail
    } catch (_) {}
    throw new Error(message)
  }

  return res.json()
}

// ─────────────────────────────────────────────
// GET /insights
// Returns: { total_events, avg_damage_usd, avg_risk_score, high_risk_states }
// ─────────────────────────────────────────────
export async function fetchInsights() {
  return request('/insights')
}

// ─────────────────────────────────────────────
// POST /predict
// Payload: { lat, lon, month, magnitude, narrative }
// Returns: { event_type, top_predictions, damage_usd, risk_score, explanation, keywords }
// ─────────────────────────────────────────────
export async function runPrediction({ lat, lon, month, magnitude, narrative }) {
  return request('/predict', {
    method: 'POST',
    body: JSON.stringify({ lat, lon, month, magnitude, narrative }),
  })
}
