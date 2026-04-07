const BASE_URL = 'http://127.0.0.1:8000'

/**
 * Get auth token from localStorage
 */
export function getAuthToken() {
  return localStorage.getItem('sentinel_token')
}

/**
 * Shared fetch wrapper with error handling.
 * Throws a structured error object on failure.
 */
async function request(path, options = {}) {
  const url = `${BASE_URL}${path}`

  // Add auth header if token exists
  const token = getAuthToken()
  const headers = {
    'Content-Type': 'application/json',
    ...(token && { 'Authorization': `Bearer ${token}` }),
  }

  const res = await fetch(url, {
    headers: { ...headers, ...options.headers },
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

// ─────────────────────────────────────────────
// AUTHENTICATION
// ─────────────────────────────────────────────
export async function loginUser(username, password) {
  // FastAPI expects form data for OAuth2, not standard JSON
  const formData = new URLSearchParams();
  formData.append('username', username);
  formData.append('password', password);
  
  const res = await fetch(`${BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: formData,
  });
  
  if (!res.ok) throw new Error('Invalid credentials');
  return res.json();
}

export async function getMe(token) {
  return request('/auth/me', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
}

export async function registerUser({ username, password, full_name }) {
  const res = await fetch(`${BASE_URL}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password, full_name }),
  });

  if (!res.ok) {
    const body = await res.json();
    throw new Error(body?.detail || 'Registration failed');
  }
  return res.json();
}
