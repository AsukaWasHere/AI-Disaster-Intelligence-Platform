import React from 'react'
import { useAuth } from '../hooks/useAuth'

export default function Topbar({ title = 'The Sentinel Perspective' }) {
  const { user, logout } = useAuth()

  return (
    <header className="h-14 border-b border-sborder flex items-center justify-between px-6 bg-sbg sticky top-0 z-20">
      <div className="font-semibold text-sm text-white tracking-wide">{title}</div>

      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 bg-ssurface border border-sborder rounded-lg px-3 py-1.5">
          <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="#4b5563" strokeWidth="2">
            <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
          </svg>
          <input
            className="bg-transparent text-xs text-slate-400 outline-none w-48 placeholder-slate-600"
            placeholder="Search global anomalies..."
          />
        </div>
        <button className="w-8 h-8 rounded-lg bg-ssurface border border-sborder flex items-center justify-center text-slate-400 hover:text-white transition-colors">
          <svg width="15" height="15" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
            <path d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>
          </svg>
        </button>
        <div className="flex items-center gap-2 bg-ssurface border border-sborder rounded-lg px-3 py-1.5 cursor-pointer hover:border-scyan transition-colors" onClick={logout}>
          <div className="w-5 h-5 rounded-full bg-gradient-to-br from-scyan to-purple-600 flex items-center justify-center">
            <svg width="10" height="10" fill="white" viewBox="0 0 24 24">
              <path d="M12 12c2.7 0 4.8-2.1 4.8-4.8S14.7 2.4 12 2.4 7.2 4.5 7.2 7.2 9.3 12 12 12zm0 2.4c-3.2 0-9.6 1.6-9.6 4.8v2.4h19.2v-2.4c0-3.2-6.4-4.8-9.6-4.8z"/>
            </svg>
          </div>
          <div className="flex flex-col items-start">
            <span className="text-xs text-white font-medium">{user?.name || 'User'}</span>
            <span className="text-[9px] text-slate-500 uppercase">{user?.role || 'Guest'}</span>
          </div>
          <svg width="10" height="10" fill="none" viewBox="0 0 24 24" stroke="#64748b" strokeWidth="2">
            <path d="M9 9l10.5-10.5m0 0L19.5 9m-10.5 0l10.5 10.5" opacity="0.5"/>
          </svg>
        </div>
      </div>
    </header>
  )
}
