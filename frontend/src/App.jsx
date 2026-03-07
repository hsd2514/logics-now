import React, { useState, useEffect } from 'react'
import {
  FileText, Upload, LayoutDashboard, ShieldAlert,
  RefreshCw, Wifi, WifiOff, Moon, Sun, BarChart2,
  ChevronLeft, ChevronRight, Sparkles, AlertTriangle,
  Download, Users, PackageCheck, ShieldCheck,
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
import { AdminDemoDashboard } from './components/AdminDemoDashboard'
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

  const [demoLoading, setDemoLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('dashboard')
  const [stats, setStats] = useState(null)
  const [statsLoading, setStatsLoading] = useState(false)
  const [selectedTriplet, setSelectedTriplet] = useState(null)
  const [compareTriplet, setCompareTriplet] = useState(null)
  const [chatDocument, setChatDocument] = useState(null)
  const [filters, setFilters] = useState({})
  const [page, setPage] = useState(1)
  const [fraudAlerts, setFraudAlerts] = useState([])
  const navItems = [
    { key: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { key: 'charts', label: 'Analytics', icon: BarChart2 },
    { key: 'upload', label: 'Documents', icon: Upload },
    { key: 'batch', label: 'Batch Upload', icon: PackageCheck },
    { key: 'vendors', label: 'Vendors', icon: Users },
    { key: 'fraud', label: 'Fraud Detection', icon: ShieldAlert },
    { key: 'admin', label: 'Admin Demo', icon: ShieldCheck },
  ]


  const { documents, fetchDocuments, uploadDocument, loading: docsLoading, error: docsError } = useDocuments()
  const { triplets, stats: tripletStats, fetchTriplets, runMatching, approveTriplet, rejectTriplet, loading: tripletsLoading, error: tripletsError } = useTriplets()
  const { isConnected, lastMessage } = useWebSocket()

  // Show hook errors as toasts
  useEffect(() => { if (docsError) toast({ type: 'error', title: 'Document error', description: docsError }) }, [docsError])
  useEffect(() => { if (tripletsError) toast({ type: 'error', title: 'Triplets error', description: tripletsError }) }, [tripletsError])

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
    } catch { }
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
  const totalPages = Math.max(1, Math.ceil(filteredTriplets.length / PAGE_SIZE))
  const pagedTriplets = filteredTriplets.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)
  useEffect(() => { setPage(1) }, [filters])

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950">

      {/* Header */}
      <header className="border-b bg-white/80 dark:bg-slate-900/80 backdrop-blur-xl sticky top-0 z-50 shadow-sm">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            {/* Logo & Branding */}
            <div className="flex items-center gap-4">
              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-br from-orange-500 via-red-500 to-purple-600 rounded-xl blur opacity-75"></div>
                <div className="relative p-2.5 rounded-xl bg-gradient-to-br from-orange-500 via-red-500 to-purple-600 shadow-lg">
                  <FileText className="h-6 w-6 text-white" />
                </div>
              </div>
              <div className="hidden sm:block">
                <h1 className="text-xl font-bold bg-gradient-to-r from-orange-600 via-red-600 to-purple-700 bg-clip-text text-transparent">FreightIQ</h1>
                <p className="text-xs text-muted-foreground">AI Document Intelligence Platform</p>
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-3">
              {/* Connection Status */}
              <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-100 dark:bg-slate-800 text-xs">
                {isConnected
                  ? <><Wifi className="h-3.5 w-3.5 text-emerald-500" /><span className="text-emerald-600 dark:text-emerald-400 font-medium">Live</span></>
                  : <><WifiOff className="h-3.5 w-3.5 text-red-500" /><span className="text-red-600 dark:text-red-400 font-medium">Offline</span></>
                }
              </div>

              {/* Demo Actions */}
              <Button
                variant="outline"
                size="sm"
                className="hidden md:flex items-center gap-2 text-xs bg-emerald-50 hover:bg-emerald-100 border-emerald-200 text-emerald-700 dark:bg-emerald-950/50 dark:hover:bg-emerald-950 dark:border-emerald-900 dark:text-emerald-400"
                onClick={() => handleGenerateDemo(false)}
                disabled={demoLoading}
              >
                <Sparkles className="h-4 w-4" />
                Demo Shipment
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="hidden md:flex items-center gap-2 text-xs bg-amber-50 hover:bg-amber-100 border-amber-200 text-amber-700 dark:bg-amber-950/50 dark:hover:bg-amber-950 dark:border-amber-900 dark:text-amber-400"
                onClick={() => handleGenerateDemo(true)}
                disabled={demoLoading}
              >
                <AlertTriangle className="h-4 w-4" />
                Demo Fraud
              </Button>

              {/* Utility Buttons */}
              <Button 
                variant="ghost" 
                size="icon" 
                onClick={handleRefresh} 
                disabled={tripletsLoading || statsLoading}
                className="hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                <RefreshCw className={`h-4 w-4 ${(tripletsLoading || statsLoading) ? 'animate-spin' : ''}`} />
              </Button>
              <Button 
                variant="ghost" 
                size="icon" 
                onClick={toggleTheme}
                className="hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
              </Button>
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="border-t border-slate-200 dark:border-slate-800">
          <div className="container mx-auto px-6">
            <div className="flex items-center gap-1 overflow-x-auto scrollbar-hide">
              {navItems.map(item => {
                const Icon = item.icon
                const isActive = activeTab === item.key
                return (
                  <button
                    key={item.key}
                    onClick={() => setActiveTab(item.key)}
                    className={`relative flex items-center gap-2 px-4 py-3 text-sm font-medium transition-all whitespace-nowrap ${
                      isActive 
                        ? 'text-primary' 
                        : 'text-muted-foreground hover:text-foreground hover:bg-slate-100 dark:hover:bg-slate-800/50'
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                    {item.label}
                    {item.key === 'fraud' && (stats?.fraud?.open_alerts || 0) > 0 && (
                      <span className="flex items-center justify-center min-w-[18px] h-[18px] text-[10px] font-bold rounded-full bg-red-500 text-white px-1">
                        {stats.fraud.open_alerts}
                      </span>
                    )}
                    {isActive && (
                      <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-orange-500 via-red-500 to-purple-600"></div>
                    )}
                  </button>
                )
              })}
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-6 py-8">
        {/* Stats Section */}
        <div className="mb-8">
          {statsLoading && !stats ? (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              {Array.from({ length: 6 }).map((_, i) => <StatsCardSkeleton key={i} />)}
            </div>
          ) : (
            <StatsCards stats={stats} />
          )}
        </div>

        {/* NL Query Bar */}
        <div className="mb-8">
          <NLQueryBar onFiltersApplied={handleFiltersApplied} />
        </div>

        {/* Tab Content */}
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
                      className={`w-full flex items-center justify-between rounded-md px-3 py-2 text-sm transition-colors ${activeTab === item.key ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'
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
            <section className="min-w-0">

              {/* Dashboard */}
              <TabsContent value="dashboard">
                {/* Action Bar */}
                <div className="flex flex-wrap items-center justify-between gap-4 mb-6 p-4 rounded-xl bg-white/60 dark:bg-slate-900/60 backdrop-blur border">
                  <div>
                    <h2 className="text-lg font-semibold">Matched Triplets</h2>
                    <p className="text-sm text-muted-foreground">{filteredTriplets.length} total matches</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button 
                      variant="outline" 
                      size="sm" 
                      onClick={() => handleExportTriplets('csv')}
                      className="gap-2"
                    >
                      <Download className="h-4 w-4" />
                      CSV
                    </Button>
                    <Button 
                      variant="outline" 
                      size="sm" 
                      onClick={() => handleExportTriplets('pdf')}
                      className="gap-2"
                    >
                      <Download className="h-4 w-4" />
                      PDF
                    </Button>
                    <Button 
                      size="sm" 
                      onClick={handleRunMatching} 
                      disabled={tripletsLoading}
                      className="bg-gradient-to-r from-orange-500 via-red-500 to-purple-600 hover:from-orange-600 hover:via-red-600 hover:to-purple-700"
                    >
                      {tripletsLoading
                        ? <><span className="animate-spin mr-2 h-4 w-4 border-2 border-current border-t-transparent rounded-full inline-block" />Matching…</>
                        : 'Run Matching'
                      }
                    </Button>
                  </div>
                </div>

                <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
                  {/* Main Content - Triplet List */}
                  <div className="xl:col-span-2 space-y-4">
                    {tripletsLoading && triplets.length === 0 ? (
                      <div className="grid gap-4">
                        {Array.from({ length: 3 }).map((_, i) => <CardSkeleton key={i} />)}
                      </div>
                    ) : pagedTriplets.length === 0 ? (
                      <Card className="border-dashed bg-white/40 dark:bg-slate-900/40">
                        <CardContent className="py-16 text-center">
                          <div className="mx-auto w-16 h-16 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center mb-4">
                            <FileText className="h-8 w-8 text-slate-400" />
                          </div>
                          <p className="text-muted-foreground text-lg mb-2">No triplets found</p>
                          <p className="text-sm text-muted-foreground">Upload documents and run matching to get started</p>
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

                        {/* Pagination */}
                        {totalPages > 1 && (
                          <div className="flex items-center justify-between p-4 rounded-xl bg-white/60 dark:bg-slate-900/60 backdrop-blur border">
                            <span className="text-sm text-muted-foreground">Page {page} of {totalPages}</span>
                            <div className="flex gap-2">
                              <Button 
                                variant="outline" 
                                size="sm" 
                                onClick={() => setPage(p => Math.max(1, p - 1))} 
                                disabled={page === 1}
                              >
                                <ChevronLeft className="h-4 w-4" />
                              </Button>
                              <Button 
                                variant="outline" 
                                size="sm" 
                                onClick={() => setPage(p => Math.min(totalPages, p + 1))} 
                                disabled={page === totalPages}
                              >
                                <ChevronRight className="h-4 w-4" />
                              </Button>
                            </div>
                          </div>
                        )}
                      </>
                    )}
                  </div>

                  {/* Sidebar - Quick Stats & Features */}
                  <div className="space-y-4">
                    {chatDocument ? (
                      <DocumentChat 
                        documentId={chatDocument.id} 
                        documentName={chatDocument.name} 
                        onClose={() => setChatDocument(null)} 
                      />
                    ) : selectedTriplet?.attention_map ? (
                      <AttentionHeatmap attentionMap={selectedTriplet.attention_map} />
                    ) : (
                      <Card className="bg-gradient-to-br from-white to-slate-50 dark:from-slate-900 dark:to-slate-800 border-slate-200 dark:border-slate-700">
                        <CardHeader>
                          <CardTitle className="text-base">Quick Stats</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                          {[
                            ['Auto-approved', tripletStats.autoApproved || 0, 'text-emerald-600 dark:text-emerald-400'],
                            ['Pending Review', tripletStats.pendingReview || 0, 'text-amber-600 dark:text-amber-400'],
                            ['Flagged', tripletStats.flagged || 0, 'text-red-600 dark:text-red-400'],
                          ].map(([label, value, colorClass]) => (
                            <div key={label} className="flex justify-between items-center p-3 rounded-lg bg-white/50 dark:bg-slate-800/50">
                              <span className="text-sm text-muted-foreground">{label}</span>
                              <span className={`text-lg font-bold ${colorClass}`}>{value}</span>
                            </div>
                          ))}
                        </CardContent>
                      </Card>
                    )}
                  </div>
                </div>
              </TabsContent>

              {/* Analytics Charts */}
              <TabsContent value="charts">
                <div className="space-y-6">
                  <div className="flex items-center justify-between p-4 rounded-xl bg-white/60 dark:bg-slate-900/60 backdrop-blur border">
                    <div>
                      <h2 className="text-lg font-semibold">Analytics & Insights</h2>
                      <p className="text-sm text-muted-foreground">Visual analytics and trends</p>
                    </div>
                  </div>
                  <DashboardCharts triplets={triplets} fraudAlerts={fraudAlerts} stats={stats} />
                </div>
              </TabsContent>

              {/* Document Upload */}
              <TabsContent value="upload">
                <div className="space-y-6">
                  <div className="p-4 rounded-xl bg-white/60 dark:bg-slate-900/60 backdrop-blur border">
                    <h2 className="text-lg font-semibold mb-1">Document Management</h2>
                    <p className="text-sm text-muted-foreground">Upload and manage your documents</p>
                  </div>
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <DocumentUpload onUpload={handleUpload} />
                    <Card className="bg-gradient-to-br from-white to-slate-50 dark:from-slate-900 dark:to-slate-800">
                      <CardHeader>
                        <CardTitle className="text-base flex items-center justify-between">
                          Recent Uploads
                          {docsLoading && <span className="text-xs font-normal text-muted-foreground animate-pulse">Loading…</span>}
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        {documents.length === 0 ? (
                          <div className="text-center py-12">
                            <div className="mx-auto w-12 h-12 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center mb-3">
                              <FileText className="h-6 w-6 text-slate-400" />
                            </div>
                            <p className="text-muted-foreground text-sm">No documents uploaded yet</p>
                          </div>
                        ) : (
                          <div className="space-y-2 max-h-[400px] overflow-y-auto pr-1">
                            {documents.slice(0, 50).map(doc => (
                              <div key={doc.id} className="flex items-center justify-between p-3 bg-white/50 dark:bg-slate-800/50 rounded-lg text-sm hover:bg-white dark:hover:bg-slate-800 transition-colors">
                                <div className="flex items-center gap-3 min-w-0 flex-1">
                                  <FileText className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
                                  <span className="truncate font-medium" title={doc.file_name}>{doc.file_name}</span>
                                </div>
                                <div className="flex items-center gap-2 flex-shrink-0">
                                  <Badge variant="outline" className="text-xs">{doc.type}</Badge>
                                  <Badge variant={doc.status === 'PROCESSED' ? 'success' : 'secondary'} className="text-xs">{doc.status}</Badge>
                                  {doc.processing_time_ms?.total && (
                                    <Badge variant="outline" className="text-xs">{(doc.processing_time_ms.total / 1000).toFixed(2)}s</Badge>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  </div>
                </div>
              </TabsContent>

              {/* Batch Upload */}
              <TabsContent value="batch">
                <div className="space-y-6">
                  <div className="p-4 rounded-xl bg-white/60 dark:bg-slate-900/60 backdrop-blur border">
                    <h2 className="text-lg font-semibold mb-1">Batch Upload</h2>
                    <p className="text-sm text-muted-foreground">Upload multiple documents at once</p>
                  </div>
                  <BatchUploadProgress />
                </div>
              </TabsContent>

              {/* Vendor Analytics */}
              <TabsContent value="vendors">
                <div className="space-y-6">
                  <div className="p-4 rounded-xl bg-white/60 dark:bg-slate-900/60 backdrop-blur border">
                    <h2 className="text-lg font-semibold mb-1">Vendor Analytics</h2>
                    <p className="text-sm text-muted-foreground">Insights and patterns from vendor data</p>
                  </div>
                  <VendorAnalytics />
                </div>
              </TabsContent>

              {/* Fraud Detection */}
              <TabsContent value="fraud">
                <div className="space-y-6">
                  <div className="flex items-center justify-between p-4 rounded-xl bg-gradient-to-r from-red-50 to-orange-50 dark:from-red-950/30 dark:to-orange-950/30 border border-red-200 dark:border-red-900">
                    <div>
                      <h2 className="text-lg font-semibold flex items-center gap-2">
                        <ShieldAlert className="h-5 w-5 text-red-600 dark:text-red-400" />
                        Fraud Detection
                      </h2>
                      <p className="text-sm text-muted-foreground">Monitor and investigate suspicious activities</p>
                    </div>
                    {(stats?.fraud?.open_alerts || 0) > 0 && (
                      <Badge className="bg-red-500 text-white text-sm px-3 py-1">
                        {stats.fraud.open_alerts} Active Alerts
                      </Badge>
                    )}
                  </div>
                  <FraudAlertPanel />
                </div>
              </TabsContent>

              {/* Admin demo */}
              <TabsContent value="admin">
                <AdminDemoDashboard onRefresh={handleRefresh} />
              </TabsContent>
            </section>
          </div>
        </Tabs>
      </main>

      {/* Comparison Modal */}
      {compareTriplet && (
        <TripletComparisonView triplet={compareTriplet} onClose={() => setCompareTriplet(null)} />
      )}

      {/* Footer */}
      <footer className="border-t bg-white/80 dark:bg-slate-900/80 backdrop-blur mt-16">
        <div className="container mx-auto px-6 py-6">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="p-1.5 rounded-lg bg-gradient-to-br from-orange-500 via-red-500 to-purple-600">
                <FileText className="h-4 w-4 text-white" />
              </div>
              <div className="text-sm">
                <p className="font-semibold text-foreground">FreightIQ</p>
                <p className="text-xs text-muted-foreground">AI Document Intelligence Platform</p>
              </div>
            </div>
            <div className="text-xs text-muted-foreground text-center md:text-right">
              <p>Team Up Up & Debug</p>
              <p>LogisticsNow Hackathon 2026</p>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default App
