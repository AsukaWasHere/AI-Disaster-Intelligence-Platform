import React from 'react'
import { useAuth } from '../hooks/useAuth'

const NavItem = ({ icon, label, active, onClick }) => (
  <button
    onClick={onClick}
    className={`nav-item w-full flex items-center gap-3 px-5 py-3 text-sm font-medium cursor-pointer ${
      active ? 'nav-item-active' : 'text-slate-400'
    }`}
  >
    <span className="text-lg">{icon}</span>
    <span>{label}</span>
  </button>
)

export default function Sidebar({ activePage, setActivePage }) {
  const { user } = useAuth()
  const navItems = [
    { id: 'overview', label: 'Overview', icon: '▪︎' },
    { id: 'predictions', label: 'Predictions', icon: '📊' },
    { id: 'geospatial', label: 'Geospatial', icon: '🌍' },
    { id: 'insights', label: 'Insights', icon: '⚙️' },
  ]

  // Fallback initials if user data is incomplete
  const getInitials = (name = '') => {
    const parts = name.trim().split(' ')
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
    return name.slice(0, 2).toUpperCase()
  }

  return (
    <aside className="w-52 bg-ssurface border-r border-sborder flex flex-col h-screen fixed left-0 top-0 z-10">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-sborder">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-scyan flex items-center justify-center" style={{background:'linear-gradient(135deg,#00e5ff,#a855f7)'}}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M8 2L13 6V14H3V6L8 2Z" stroke="white" strokeWidth="1.5" strokeLinejoin="round"/>
              <circle cx="8" cy="9" r="2" fill="white"/>
            </svg>
          </div>
          <div>
            <div className="text-xs font-bold text-white leading-tight">AI Disaster</div>
            <div className="text-xs font-bold text-white leading-tight">Intelligence</div>
            <div className="text-[9px] text-slate-500 uppercase tracking-widest mt-0.5">Global Command</div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4">
        {navItems.map(item => (
          <NavItem
            key={item.id}
            icon={item.icon}
            label={item.label}
            active={activePage === item.id}
            onClick={() => setActivePage(item.id)}
          />
        ))}
      </nav>

      {/* User */}
      <div className="px-5 py-4 border-t border-sborder">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold"
            style={{background:'linear-gradient(135deg,#f59e0b,#ef4444)'}}>
            {user?.name ? getInitials(user.name) : 'MC'}
          </div>
          <div>
            <div className="text-xs font-semibold text-white truncate max-w-[90px]">
              {user?.name || 'User'}
            </div>
            <div className="text-[10px] text-slate-500 truncate max-w-[90px]">
              {user?.role || 'Guest'}
            </div>
          </div>
        </div>
      </div>
    </aside>
  )
}
