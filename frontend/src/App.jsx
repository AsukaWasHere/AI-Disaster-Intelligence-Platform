import React, { useState } from 'react'
import Sidebar from './components/Sidebar'
import Topbar from './components/Topbar'
import OverviewPage from './pages/OverviewPage'
import PredictionsPage from './pages/PredictionsPage'
import GeospatialPage from './pages/GeospatialPage'
import InsightsPage from './pages/InsightsPage'

export default function App() {
  const [activePage, setActivePage] = useState('overview')

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
