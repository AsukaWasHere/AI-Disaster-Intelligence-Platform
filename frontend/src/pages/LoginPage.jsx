import React, { useState } from 'react'
import { loginUser } from '../services/api'
import { useAuth } from '../hooks/useAuth'
import LoadingSpinner from '../components/LoadingSpinner'

export default function LoginPage() {
  const [form, setForm] = useState({ username: '', password: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()

  const handleSubmit = async (e) => {
    e?.preventDefault()
    setError('')
    setLoading(true)

    try {
      const data = await loginUser(form.username, form.password)
      login({ username: data.username, name: data.name, role: data.role }, data.access_token)
    } catch (err) {
      setError(err.message || 'Login failed. Please check your credentials.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-[#080d1a]">
      <div className="w-full max-w-md p-8">
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-3 mb-4">
            <div className="w-12 h-12 rounded-xl bg-scyan flex items-center justify-center shadow-lg shadow-cyan-500/20">
              <svg width="24" height="24" viewBox="0 0 16 16" fill="none">
                <path d="M8 2L13 6V14H3V6L8 2Z" stroke="#00e5ff" strokeWidth="1.5" strokeLinejoin="round"/>
                <circle cx="8" cy="9" r="2" fill="#00e5ff"/>
              </svg>
            </div>
            <div className="text-left">
              <div className="text-2xl font-bold text-white tracking-tight">AI Disaster</div>
              <div className="text-lg font-bold text-white tracking-tight">Intelligence</div>
            </div>
          </div>
          <p className="text-slate-500 text-sm">Global Command System</p>
        </div>

        <div className="bg-ssurface border border-sborder rounded-2xl p-8 shadow-2xl shadow-black/50">
          <h2 className="text-xl font-bold text-white mb-6">Sign In</h2>

          {error && (
            <div className="mb-6 p-3 rounded-lg bg-red-950/50 border border-red-900/50">
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-2">
                Username
              </label>
              <input
                type="text"
                className="w-full bg-[#0a1628] border border-sborder rounded-lg px-4 py-3 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-scyan transition-colors"
                placeholder="Enter your username"
                value={form.username}
                onChange={e => setForm(p => ({ ...p, username: e.target.value }))}
                required
              />
            </div>

            <div>
              <label className="block text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-2">
                Password
              </label>
              <input
                type="password"
                className="w-full bg-[#0a1628] border border-sborder rounded-lg px-4 py-3 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-scyan transition-colors"
                placeholder="Enter your password"
                value={form.password}
                onChange={e => setForm(p => ({ ...p, password: e.target.value }))}
                required
              />
            </div>

            <button
              type="submit"
              className="btn-primary w-full py-3.5 rounded-xl text-sm font-bold uppercase tracking-widest disabled:opacity-60 disabled:cursor-not-allowed shadow-lg shadow-scyan-500/20 transition-all hover:shadow-scyan-500/30"
              disabled={loading}
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <LoadingSpinner label="" size="sm" />
                  Authenticating...
                </span>
              ) : (
                'Initialize System'
              )}
            </button>
          </form>

          <div className="mt-6 pt-6 border-t border-sborder">
            <div className="text-[10px] text-slate-600 text-center">
              <p className="mb-2">Demo Credentials (in-memory):</p>
              <div className="flex justify-center gap-4">
                <span className="text-slate-500">Username: <span className="text-slate-400">admin</span></span>
                <span className="text-slate-500">Password: <span className="text-slate-400">password</span></span>
              </div>
            </div>
          </div>
        </div>

        <div className="text-center mt-6">
          <p className="text-[10px] text-slate-700">
            Secure System v1.0.0 &copy; 2026 AI Disaster Intelligence
          </p>
        </div>
      </div>
    </div>
  )
}
