import { useState } from 'react'
import Sidebar from './components/Sidebar'
import Topbar from './components/Topbar'
import OverviewPage from './pages/OverviewPage'
import PredictionsPage from './pages/PredictionsPage'
import GeospatialPage from './pages/GeospatialPage'
import InsightsPage from './pages/InsightsPage'
import LoginPage from './pages/LoginPage'
import { useAuth } from './hooks/useAuth'

export default function App() {
  const [activePage, setActivePage] = useState('overview')
  const { user } = useAuth()

  // If there is no user in memory, stop here and show the Login Page instead
  if (!user) {
    return <LoginPage />
  }

  const pageMap = {
    overview: <OverviewPage />,
    predictions: <PredictionsPage />,
    geospatial: <GeospatialPage />,
    insights: <InsightsPage />,
  }

  const isGeo = activePage === 'geospatial'

  return (
    <div className="flex h-screen bg-sbg overflow-hidden" style={{ background: '#080d1a' }}>
      <Sidebar activePage={activePage} setActivePage={setActivePage} />

      <div className="flex-1 flex flex-col ml-52 overflow-hidden">
        <Topbar />
        <main className={`flex-1 ${isGeo ? 'overflow-hidden relative' : 'overflow-y-auto'}`}>
          {pageMap[activePage]}
        </main>
      </div>
    </div>
  )
}
