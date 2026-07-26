import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Header from './components/Header.jsx'
import Footer from './components/Footer.jsx'
import AlertsBanner from './components/AlertsBanner.jsx'
import { ensureClientKey } from './api/client.js'

// Lazy load route pages for performance & initial bundle optimization
const Home = lazy(() => import('./pages/Home.jsx'))
const CheckResult = lazy(() => import('./pages/CheckResult.jsx'))
const RegisterMonitor = lazy(() => import('./pages/RegisterMonitor.jsx'))
const MyMonitors = lazy(() => import('./pages/MyMonitors.jsx'))
const MonitorDetail = lazy(() => import('./pages/MonitorDetail.jsx'))

// Generate client key on first visit (App Flow §0.1)
ensureClientKey()

function PageFallback() {
  return (
    <div className="page-container animate-fade-in" style={{ padding: '60px 0' }}>
      <div className="skeleton" style={{ height: '48px', width: '60%', marginBottom: '24px' }}></div>
      <div className="skeleton" style={{ height: '24px', width: '40%', marginBottom: '40px' }}></div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px' }}>
        <div className="skeleton" style={{ height: '180px' }}></div>
        <div className="skeleton" style={{ height: '180px' }}></div>
        <div className="skeleton" style={{ height: '180px' }}></div>
      </div>
    </div>
  )
}

function App() {
  return (
    <BrowserRouter basename="/url-audit-project">
      <Header />
      <main className="page-container">
        <AlertsBanner />
        <Suspense fallback={<PageFallback />}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/result/:auditId" element={<CheckResult />} />
            <Route path="/monitors/new" element={<RegisterMonitor />} />
            <Route path="/monitors" element={<MyMonitors />} />
            <Route path="/monitors/:monitorId" element={<MonitorDetail />} />
          </Routes>
        </Suspense>
      </main>
      <Footer />
    </BrowserRouter>
  )
}

export default App
