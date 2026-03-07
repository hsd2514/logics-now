import React, { useState, useEffect } from 'react'
import {
  FileText, Upload, LayoutDashboard, ShieldAlert,
  RefreshCw, Wifi, WifiOff, Moon, Sun, BarChart2,
  ChevronLeft, ChevronRight, Sparkles, AlertTriangle,
  Download, Users, PackageCheck,
} from 'lucide-react'
import { Button } from './components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from './components/ui/card'
import { Tabs, TabsContent } from './components/ui/tabs'
import { Badge } from './components/ui/badge'
import { DocumentUpload } from './components/DocumentUpload'
import { TripletCard } from './components/TripletCard'
import { TripletComparisonView } from './components/TripletComparisonView'
import { FraudAlertPanel } from './components/FraudAlertPanel'
import { NLQueryBar } from './components/NLQueryBar'
import { DocumentChat } from './components/DocumentChat'
import { StatsCards } from './components/StatsCards'
import { AttentionHeatmap } from './components/AttentionHeatmap'
import { DashboardCharts } from './components/DashboardCharts'
import { VendorAnalytics } from './components/VendorAnalytics'
import { BatchUploadProgress } from './components/BatchUploadProgress'
import { CardSkeleton, StatsCardSkeleton } from './components/Skeleton'
import { useDocuments } from './hooks/useDocuments'
import { useTriplets } from './hooks/useTriplets'
import { useWebSocket } from './hooks/useWebSocket'
import { useTheme } from './hooks/useTheme'
import { useToast } from './components/Toaster'
import * as api from './services/api'

const PAGE_SIZE = 8

function App() {
  const toast = useToast()
  const { isDark, toggle: toggleTheme } = useTheme()

  const [demoLoading,     setDemoLoading]     = useState(false)
  const [activeTab,       setActiveTab]       = useState('dashboard')
  const [stats,           setStats]           = useState(null)
  const [statsLoading,    setStatsLoading]    = useState(false)
  const [selectedTriplet, setSelectedTriplet] = useState(null)
  const [compareTriplet,  setCompareTriplet]  = useState(null)
  const [chatDocument,    setChatDocument]    = useState(null)
  const [filters,         setFilters]         = useState({})
  const [page,            setPage]            = useState(1)
  const [fraudAlerts,     setFraudAlerts]     = useState([])
  const navItems = [
    { key: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { key: 'charts', label: 'Analytics', icon: BarChart2 },
    { key: 'upload', label: 'Documents', icon: Upload },
    { key: 'batch', label: 'Batch Upload', icon: PackageCheck },
    { key: 'vendors', label: 'Vendors', icon: Users },
    { key: 'fraud', label: 'Fraud Detection', icon: ShieldAlert },
  ]

  const { documents, fetchDocuments, uploadDocument, loading: docsLoading, error: docsError } = useDocuments()
  const { triplets, stats: tripletStats, fetchTriplets, runMatching, approveTriplet, rejectTriplet, loading: tripletsLoading, error: tripletsError } = useTriplets()
  const { isConnected, lastMessage } = useWebSocket()

  // Show hook errors as toasts
  useEffect(() => { if (docsError)     toast({ type: 'error', title: 'Document error',  description: docsError })     }, [docsError])
  useEffect(() => { if (tripletsError) toast({ type: 'error', title: 'Triplets error',  description: tripletsError }) }, [tripletsError])

  useEffect(() => {
    fetchStats()
    fetchDocuments()
    fetchTriplets()
    fetchFraudAlerts()
  }, [])

  useEffect(() => {
    if (!lastMessage) return
    if (lastMessage.type === 'match_found') {
      fetchTriplets(); fetchStats()
      toast({ type: 'success', title: 'New match found!', description: 'Triplet list updated.' })
    }
    if (lastMessage.type === 'fraud_alert') {
      fetchStats(); fetchFraudAlerts()
      toast({ type: 'warning', title: 'Fraud alert detected', description: lastMessage.message || '' })
    }
  }, [lastMessage])

  const fetchStats = async () => {
    setStatsLoading(true)
    try {
      const response = await api.getStats()
      setStats(response.data)
    } catch (err) {
      toast({ type: 'error', title: 'Failed to load stats', description: err.message })
    } finally {
      setStatsLoading(false)
    }
  }

  const fetchFraudAlerts = async () => {
    try {
      const response = await api.getFraudAlerts({})
      setFraudAlerts(response.data.alerts || [])
    } catch {}
  }

  const handleUpload = async (file, docType) => {
    try {
      const result = await uploadDocument(file, docType)
      fetchStats()
      toast({ type: 'success', title: 'Document uploaded', description: `${docType} processed successfully.` })
      return result
    } catch (err) {
      toast({ type: 'error', title: 'Upload failed', description: err.message })
    }
  }

  const handleRunMatching = async () => {
    try {
      await runMatching()
      fetchStats()
      toast({ type: 'success', title: 'Matching complete', description: 'Triplets have been updated.' })
    } catch (err) {
      toast({ type: 'error', title: 'Matching failed', description: err.message })
    }
  }

  const handleApprove = async (id) => {
    try { await approveTriplet(id); toast({ type: 'success', title: 'Triplet approved' }) }
    catch (err) { toast({ type: 'error', title: 'Approval failed', description: err.message }) }
  }

  const handleReject = async (id) => {
    try { await rejectTriplet(id); toast({ type: 'warning', title: 'Triplet rejected' }) }
    catch (err) { toast({ type: 'error', title: 'Rejection failed', description: err.message }) }
  }

  const handleFiltersApplied = (newFilters) => {
    setFilters(newFilters); setPage(1); fetchTriplets(newFilters)
  }

  const handleRefresh = () => {
    fetchStats(); fetchTriplets(filters); fetchDocuments(); fetchFraudAlerts()
    toast({ type: 'info', title: 'Refreshed' })
  }

  const downloadBlob = (blob, fileName) => {
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = fileName
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleExportTriplets = async (format = 'csv') => {
    try {
      const res = await api.exportTriplets(format)
      downloadBlob(res.data, `triplets_export.${format}`)
      toast({ type: 'success', title: `Triplets ${format.toUpperCase()} exported` })
    } catch (e) {
      toast({ type: 'error', title: 'Triplet export failed', description: e.message })
    }
  }

  const handleExportAudit = async (tripletId, format = 'pdf') => {
    try {
      const res = await api.exportTripletAudit(tripletId, format)
      downloadBlob(res.data, `triplet_audit_${tripletId.slice(0, 8)}.${format}`)
      toast({ type: 'success', title: `Audit ${format.toUpperCase()} exported` })
    } catch (e) {
      toast({ type: 'error', title: 'Audit export failed', description: e.message })
    }
  }

  // Pagination
  const handleGenerateDemo = async (anomaly = false) => {
    setDemoLoading(true)
    try {
      const res = await api.generateDemo(anomaly)
      const d = res.data
      toast({
        type: anomaly ? 'warning' : 'success',
        title: anomaly ? '⚠️ Anomalous Shipment Generated' : '✅ Demo Shipment Generated',
        description: `${d.shipment_id} — ${d.triplets_created} triplet(s) matched. Refreshing…`,
      })
      setTimeout(handleRefresh, 600)
    } catch (e) {
      toast({ type: 'error', title: 'Demo generation failed', description: e?.response?.data?.detail || e.message })
    } finally {
      setDemoLoading(false)
    }
  }

  const filteredTriplets = triplets.filter(t => {
    if (filters.status && t.status !== filters.status) return false
    return true
  })
  const totalPages    = Math.max(1, Math.ceil(filteredTriplets.length / PAGE_SIZE))
  const pagedTriplets = filteredTriplets.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)
  useEffect(() => { setPage(1) }, [filters])

  return (
    <div className="min-h-screen bg-background text-foreground">

      {/* Header */}
      <header className="border-b bg-card sticky top-0 z-40">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-gradient-to-br from-orange-500 via-red-500 to-yellow-500 shadow-sm">
                <FileText className="h-5 w-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-bold leading-none">FreightIQ</h1>
                <p className="text-[11px] text-muted-foreground">Team Up Up & Debug · LogisticsNow Hackathon 2026</p>
              </div>
              <Badge className="hidden md:inline-flex bg-amber-100 text-amber-800 border border-amber-300">Hackathon Demo</Badge>
            </div>
            <div className="flex items-center gap-2">
              <div className="hidden sm:flex items-center gap-1.5 text-xs">
                {isConnected
                  ? <><Wifi    className="h-3.5 w-3.5 text-green-500" /><span className="text-green-600">Live</span></>
                  : <><WifiOff className="h-3.5 w-3.5 text-red-500"  /><span className="text-red-600">Offline</span></>
                }
              </div>
              {/* Demo buttons */}
              <Button
                variant="outline"
                size="sm"
                className="hidden sm:flex items-center gap-1.5 text-xs h-8 text-green-700 border-green-300 hover:bg-green-50 dark:text-green-400 dark:border-green-700 dark:hover:bg-green-950"
                onClick={() => handleGenerateDemo(false)}
                disabled={demoLoading}
                title="Generate a healthy matched shipment"
              >
                <Sparkles className="h-3.5 w-3.5" />
                {demoLoading ? 'Generating…' : 'Demo Shipment'}
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="hidden sm:flex items-center gap-1.5 text-xs h-8 text-orange-700 border-orange-300 hover:bg-orange-50 dark:text-orange-400 dark:border-orange-700 dark:hover:bg-orange-950"
                onClick={() => handleGenerateDemo(true)}
                disabled={demoLoading}
                title="Generate a suspicious shipment with amount anomaly"
              >
                <AlertTriangle className="h-3.5 w-3.5" />
                {demoLoading ? 'Generating…' : 'Demo Fraud'}
              </Button>
              <Button variant="ghost" size="icon" onClick={handleRefresh} disabled={tripletsLoading || statsLoading}>
                <RefreshCw className={`h-4 w-4 ${(tripletsLoading || statsLoading) ? 'animate-spin' : ''}`} />
              </Button>
              {/* #21 Dark mode toggle */}
              <Button variant="ghost" size="icon" onClick={toggleTheme} title="Toggle dark mode">
                {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-6">
        {/* Stats (#21 loading skeleton) */}
        <div className="mb-6">
          {statsLoading && !stats ? (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              {Array.from({ length: 6 }).map((_, i) => <StatsCardSkeleton key={i} />)}
            </div>
          ) : (
            <StatsCards stats={stats} />
          )}
        </div>

        {/* NL Query */}
        <div className="mb-6">
          <NLQueryBar onFiltersApplied={handleFiltersApplied} />
        </div>

        <Tabs value={activeTab} onValueChange={t => { setActiveTab(t); setPage(1) }}>
          <div className="grid grid-cols-1 lg:grid-cols-[240px_1fr] gap-6">
            <aside className="rounded-xl border bg-card p-3 h-fit lg:sticky lg:top-20">
              <div className="mb-3 text-xs uppercase tracking-wide text-muted-foreground">Navigation</div>
              <div className="space-y-1">
                {navItems.map(item => {
                  const Icon = item.icon
                  return (
                    <button
                      key={item.key}
                      onClick={() => setActiveTab(item.key)}
                      className={`w-full flex items-center justify-between rounded-md px-3 py-2 text-sm transition-colors ${
                        activeTab === item.key ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'
                      }`}
                    >
                      <span className="flex items-center gap-2">
                        <Icon className="h-4 w-4" />
                        {item.label}
                      </span>
                      {item.key === 'fraud' && (stats?.fraud?.open_alerts || 0) > 0 && (
                        <span className="text-[10px] rounded px-1.5 py-0.5 bg-red-500 text-white">{stats.fraud.open_alerts}</span>
                      )}
                    </button>
                  )
                })}
              </div>
              <div className="mt-4 pt-4 border-t space-y-2">
                <Button variant="outline" size="sm" className="w-full justify-start" onClick={() => handleExportTriplets('csv')}>
                  <Download className="h-4 w-4 mr-2" /> Export Triplets CSV
                </Button>
                <Button variant="outline" size="sm" className="w-full justify-start" onClick={() => handleExportTriplets('pdf')}>
                  <Download className="h-4 w-4 mr-2" /> Export Triplets PDF
                </Button>
              </div>
            </aside>
            <section>

          {/* Dashboard */}
          <TabsContent value="dashboard">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-base font-semibold">
                    Matched Triplets
                    <span className="ml-2 text-xs text-muted-foreground font-normal">({filteredTriplets.length} total)</span>
                  </h2>
                  <Button size="sm" onClick={handleRunMatching} disabled={tripletsLoading}>
                    {tripletsLoading
                      ? <><span className="animate-spin mr-1.5 h-3.5 w-3.5 border-2 border-current border-t-transparent rounded-full inline-block" />Matching…</>
                      : 'Run Matching'
                    }
                  </Button>
                </div>

                {/* #21 Loading skeletons */}
                {tripletsLoading && triplets.length === 0 ? (
                  <div className="grid gap-4">
                    {Array.from({ length: 3 }).map((_, i) => <CardSkeleton key={i} />)}
                  </div>
                ) : pagedTriplets.length === 0 ? (
                  <Card>
                    <CardContent className="py-12 text-center text-muted-foreground">
                      <FileText className="h-12 w-12 mx-auto mb-2 opacity-20" />
                      <p>No triplets found. Upload documents and run matching.</p>
                    </CardContent>
                  </Card>
                ) : (
                  <>
                    <div className="grid gap-4">
                      {pagedTriplets.map(triplet => (
                        <TripletCard
                          key={triplet.id}
                          triplet={triplet}
                          onApprove={handleApprove}
                          onReject={handleReject}
                          onViewDetails={t => { setSelectedTriplet(t); setCompareTriplet(t) }}
                          onChat={() => setChatDocument({ id: triplet.lr_id, name: 'LR Document' })}
                          onExportAudit={(t) => handleExportAudit(t.id, 'pdf')}
                        />
                      ))}
                    </div>

                    {/* #21 Pagination */}
                    {totalPages > 1 && (
                      <div className="flex items-center justify-between text-sm mt-2">
                        <span className="text-muted-foreground">Page {page} of {totalPages}</span>
                        <div className="flex gap-2">
                          <Button variant="outline" size="sm" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>
                            <ChevronLeft className="h-4 w-4" />
                          </Button>
                          <Button variant="outline" size="sm" onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}>
                            <ChevronRight className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>

              {/* Sidebar */}
              <div className="space-y-4">
                {chatDocument ? (
                  <DocumentChat documentId={chatDocument.id} documentName={chatDocument.name} onClose={() => setChatDocument(null)} />
                ) : selectedTriplet?.attention_map ? (
                  <AttentionHeatmap attentionMap={selectedTriplet.attention_map} />
                ) : (
                  <Card>
                    <CardHeader><CardTitle className="text-sm">Quick Stats</CardTitle></CardHeader>
                    <CardContent className="space-y-3">
                      {[
                        ['Auto-approved', tripletStats.autoApproved || 0],
                        ['Pending Review', tripletStats.pendingReview || 0],
                        ['Flagged', tripletStats.flagged || 0],
                      ].map(([label, value]) => (
                        <div key={label} className="flex justify-between text-sm">
                          <span className="text-muted-foreground">{label}</span>
                          <span className="font-medium">{value}</span>
                        </div>
                      ))}
                    </CardContent>
                  </Card>
                )}
              </div>
            </div>
          </TabsContent>

          {/* #22 Charts tab */}
          <TabsContent value="charts">
            <div className="space-y-4">
              <h2 className="text-base font-semibold">Data Visualisation</h2>
              <DashboardCharts triplets={triplets} fraudAlerts={fraudAlerts} stats={stats} />
            </div>
          </TabsContent>

          {/* Upload */}
          <TabsContent value="upload">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <DocumentUpload onUpload={handleUpload} />
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">
                    Recent Uploads
                    {docsLoading && <span className="ml-2 text-xs font-normal text-muted-foreground animate-pulse">Loading…</span>}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {documents.length === 0 ? (
                    <p className="text-muted-foreground text-center py-6 text-sm">No documents uploaded yet</p>
                  ) : (
                    <div className="space-y-2 max-h-[360px] overflow-y-auto pr-1">
                      {documents.slice(0, 50).map(doc => (
                        <div key={doc.id} className="flex items-center justify-between p-2 bg-muted rounded text-sm">
                          <div className="flex items-center gap-2 min-w-0">
                            <FileText className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
                            <span className="truncate max-w-[180px]" title={doc.file_name}>{doc.file_name}</span>
                          </div>
                          <div className="flex items-center gap-2 flex-shrink-0">
                            <Badge variant="outline" className="text-xs">{doc.type}</Badge>
                            <Badge variant={doc.status === 'PROCESSED' ? 'success' : 'secondary'} className="text-xs">{doc.status}</Badge>
                            {doc.processing_time_ms?.total ? (
                              <Badge variant="outline" className="text-xs">{(doc.processing_time_ms.total / 1000).toFixed(2)}s</Badge>
                            ) : null}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* #30 Batch Upload */}
          <TabsContent value="batch">
            <BatchUploadProgress />
          </TabsContent>

          {/* #28 Vendor Analytics */}
          <TabsContent value="vendors">
            <VendorAnalytics />
          </TabsContent>

          {/* Fraud */}
          <TabsContent value="fraud">
            <FraudAlertPanel />
          </TabsContent>
            </section>
          </div>
        </Tabs>
      </main>

      {/* #23 Side-by-side comparison modal */}
      {compareTriplet && (
        <TripletComparisonView triplet={compareTriplet} onClose={() => setCompareTriplet(null)} />
      )}

      <footer className="border-t mt-10 py-4">
        <div className="container mx-auto px-4 text-center text-xs text-muted-foreground">
          FreightIQ · AI Document Intelligence for LR-POD-Invoice Matching · Team Up Up &amp; Debug
        </div>
      </footer>
    </div>
  )
}

export default App
