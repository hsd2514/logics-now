import React, { useState, useEffect } from 'react'
import { 
  FileText, Upload, LayoutDashboard, ShieldAlert, 
  Settings, RefreshCw, Wifi, WifiOff 
} from 'lucide-react'
import { Button } from './components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from './components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs'
import { Badge } from './components/ui/badge'
import { DocumentUpload } from './components/DocumentUpload'
import { TripletCard } from './components/TripletCard'
import { FraudAlertPanel } from './components/FraudAlertPanel'
import { NLQueryBar } from './components/NLQueryBar'
import { DocumentChat } from './components/DocumentChat'
import { StatsCards } from './components/StatsCards'
import { AttentionHeatmap } from './components/AttentionHeatmap'
import { useDocuments } from './hooks/useDocuments'
import { useTriplets } from './hooks/useTriplets'
import { useWebSocket } from './hooks/useWebSocket'
import * as api from './services/api'

function App() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [stats, setStats] = useState(null)
  const [selectedTriplet, setSelectedTriplet] = useState(null)
  const [chatDocument, setChatDocument] = useState(null)
  const [filters, setFilters] = useState({})

  const { documents, fetchDocuments, uploadDocument, loading: docsLoading } = useDocuments()
  const { triplets, stats: tripletStats, fetchTriplets, runMatching, approveTriplet, rejectTriplet, loading: tripletsLoading } = useTriplets()
  const { isConnected, lastMessage } = useWebSocket()

  useEffect(() => {
    fetchStats()
    fetchDocuments()
    fetchTriplets()
  }, [])

  useEffect(() => {
    if (lastMessage?.type === 'match_found') {
      fetchTriplets()
      fetchStats()
    }
    if (lastMessage?.type === 'fraud_alert') {
      fetchStats()
    }
  }, [lastMessage])

  const fetchStats = async () => {
    try {
      const response = await api.getStats()
      setStats(response.data)
    } catch (err) {
      console.error('Failed to fetch stats:', err)
    }
  }

  const handleUpload = async (file, docType) => {
    const result = await uploadDocument(file, docType)
    fetchStats()
    return result
  }

  const handleRunMatching = async () => {
    await runMatching()
    fetchStats()
  }

  const handleFiltersApplied = (newFilters) => {
    setFilters(newFilters)
    fetchTriplets(newFilters)
  }

  const filteredTriplets = triplets.filter(t => {
    if (filters.status && t.status !== filters.status) return false
    return true
  })

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary rounded-lg">
                <FileText className="h-6 w-6 text-primary-foreground" />
              </div>
              <div>
                <h1 className="text-xl font-bold">FreightIQ</h1>
                <p className="text-xs text-muted-foreground">AI Document Intelligence</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 text-sm">
                {isConnected ? (
                  <><Wifi className="h-4 w-4 text-green-500" /> <span className="text-green-600">Connected</span></>
                ) : (
                  <><WifiOff className="h-4 w-4 text-red-500" /> <span className="text-red-600">Disconnected</span></>
                )}
              </div>
              <Button variant="outline" size="sm" onClick={() => { fetchStats(); fetchTriplets(); }}>
                <RefreshCw className="h-4 w-4 mr-1" />
                Refresh
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-6">
        {/* Stats */}
        <div className="mb-6">
          <StatsCards stats={stats} />
        </div>

        {/* NL Query Bar (Novel Feature) */}
        <div className="mb-6">
          <NLQueryBar onFiltersApplied={handleFiltersApplied} />
        </div>

        {/* Main Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="mb-4">
            <TabsTrigger value="dashboard">
              <LayoutDashboard className="h-4 w-4 mr-1" />
              Dashboard
            </TabsTrigger>
            <TabsTrigger value="upload">
              <Upload className="h-4 w-4 mr-1" />
              Upload
            </TabsTrigger>
            <TabsTrigger value="fraud">
              <ShieldAlert className="h-4 w-4 mr-1" />
              Fraud Alerts
              {stats?.fraud?.open_alerts > 0 && (
                <Badge variant="destructive" className="ml-2">{stats.fraud.open_alerts}</Badge>
              )}
            </TabsTrigger>
          </TabsList>

          {/* Dashboard Tab */}
          <TabsContent value="dashboard">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Triplet List */}
              <div className="lg:col-span-2 space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold">Matched Triplets</h2>
                  <Button onClick={handleRunMatching} disabled={tripletsLoading}>
                    {tripletsLoading ? 'Matching...' : 'Run Matching'}
                  </Button>
                </div>
                
                {filteredTriplets.length === 0 ? (
                  <Card>
                    <CardContent className="py-8 text-center text-muted-foreground">
                      <FileText className="h-12 w-12 mx-auto mb-2 opacity-20" />
                      <p>No triplets found. Upload documents and run matching.</p>
                    </CardContent>
                  </Card>
                ) : (
                  <div className="grid gap-4">
                    {filteredTriplets.map(triplet => (
                      <TripletCard
                        key={triplet.id}
                        triplet={triplet}
                        onApprove={approveTriplet}
                        onReject={rejectTriplet}
                        onViewDetails={setSelectedTriplet}
                        onChat={() => setChatDocument({ id: triplet.lr_id, name: 'LR Document' })}
                      />
                    ))}
                  </div>
                )}
              </div>

              {/* Sidebar */}
              <div className="space-y-4">
                {/* Document Chat (Novel Feature) */}
                {chatDocument ? (
                  <DocumentChat
                    documentId={chatDocument.id}
                    documentName={chatDocument.name}
                    onClose={() => setChatDocument(null)}
                  />
                ) : selectedTriplet?.attention_map ? (
                  <AttentionHeatmap attentionMap={selectedTriplet.attention_map} />
                ) : (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">Quick Stats</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Auto-approved</span>
                        <span className="font-medium">{tripletStats.autoApproved || 0}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Pending Review</span>
                        <span className="font-medium">{tripletStats.pendingReview || 0}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Flagged</span>
                        <span className="font-medium">{tripletStats.flagged || 0}</span>
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>
            </div>
          </TabsContent>

          {/* Upload Tab */}
          <TabsContent value="upload">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <DocumentUpload onUpload={handleUpload} />
              
              <Card>
                <CardHeader>
                  <CardTitle>Recent Uploads</CardTitle>
                </CardHeader>
                <CardContent>
                  {documents.length === 0 ? (
                    <p className="text-muted-foreground text-center py-4">No documents uploaded yet</p>
                  ) : (
                    <div className="space-y-2 max-h-[400px] overflow-y-auto">
                      {documents.slice(0, 20).map(doc => (
                        <div key={doc.id} className="flex items-center justify-between p-2 bg-muted rounded">
                          <div className="flex items-center gap-2">
                            <FileText className="h-4 w-4" />
                            <span className="text-sm truncate max-w-[200px]">{doc.file_name}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <Badge variant="outline">{doc.type}</Badge>
                            <Badge variant={doc.status === 'PROCESSED' ? 'success' : 'secondary'}>
                              {doc.status}
                            </Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Fraud Tab */}
          <TabsContent value="fraud">
            <FraudAlertPanel />
          </TabsContent>
        </Tabs>
      </main>

      {/* Footer */}
      <footer className="border-t mt-8 py-4">
        <div className="container mx-auto px-4 text-center text-sm text-muted-foreground">
          FreightIQ - AI Document Intelligence for LR-POD-Invoice Matching | Team Up Up & Debug
        </div>
      </footer>
    </div>
  )
}

export default App
