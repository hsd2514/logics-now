import React, { useState, useEffect } from 'react'
import { X, CheckCircle2, XCircle, AlertCircle, FileText, ChevronDown, ChevronUp } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Badge } from './ui/badge'
import * as api from '../services/api'

const DOC_COLORS = {
  LR:      { bg: 'bg-blue-50 dark:bg-blue-950',   border: 'border-blue-200 dark:border-blue-800',   text: 'text-blue-700 dark:text-blue-300',   dot: 'bg-blue-500' },
  POD:     { bg: 'bg-green-50 dark:bg-green-950',  border: 'border-green-200 dark:border-green-800',  text: 'text-green-700 dark:text-green-300',  dot: 'bg-green-500' },
  INVOICE: { bg: 'bg-purple-50 dark:bg-purple-950',border: 'border-purple-200 dark:border-purple-800',text: 'text-purple-700 dark:text-purple-300', dot: 'bg-purple-500' },
}

const FIELD_LABELS = {
  shipment_id:    'Shipment ID',
  amount:         'Amount',
  date:           'Date',
  party_name:     'Party Name',
  origin:         'Origin',
  destination:    'Destination',
  vehicle_number: 'Vehicle No.',
  weight:         'Weight',
  gst_number:     'GST Number',
}

function MatchDot({ score }) {
  if (score === undefined || score === null) return null
  if (score >= 0.9) return <CheckCircle2 className="h-4 w-4 text-green-500 flex-shrink-0" title="Strong match" />
  if (score >= 0.6) return <AlertCircle  className="h-4 w-4 text-yellow-500 flex-shrink-0" title="Partial match" />
  return                   <XCircle      className="h-4 w-4 text-red-500   flex-shrink-0" title="Mismatch" />
}

function DocPanel({ label, doc, color }) {
  const [expanded, setExpanded] = useState(false)
  if (!doc) return (
    <div className={`flex-1 rounded-lg border-2 border-dashed ${color.border} p-4 text-center text-muted-foreground text-sm`}>
      <FileText className="h-8 w-8 mx-auto mb-2 opacity-30" />
      {label} not found
    </div>
  )
  return (
    <div className={`flex-1 rounded-lg border-2 ${color.border} ${color.bg} overflow-hidden`}>
      <div className={`px-4 py-2 flex items-center gap-2 font-semibold text-sm ${color.text}`}>
        <span className={`w-2 h-2 rounded-full ${color.dot}`} />
        {label}
        <Badge variant="outline" className="ml-auto text-xs">{doc.type}</Badge>
      </div>
      <div className="px-4 pb-3 space-y-1 text-xs">
        <div className="flex justify-between py-0.5">
          <span className="text-muted-foreground">File</span>
          <span className="font-mono truncate max-w-[140px]" title={doc.file_name}>{doc.file_name}</span>
        </div>
        <div className="flex justify-between py-0.5">
          <span className="text-muted-foreground">Status</span>
          <Badge variant={doc.status === 'PROCESSED' ? 'success' : 'secondary'} className="text-xs py-0">{doc.status}</Badge>
        </div>
        <div className="flex justify-between py-0.5">
          <span className="text-muted-foreground">OCR Conf.</span>
          <span>{doc.ocr_confidence ? `${Math.round(doc.ocr_confidence * 100)}%` : '–'}</span>
        </div>
        {doc.ocr_text && (
          <div className="pt-2">
            <button
              className={`w-full flex items-center justify-between text-xs font-medium ${color.text}`}
              onClick={() => setExpanded(v => !v)}
            >
              Raw OCR Text {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            </button>
            {expanded && (
              <pre className="mt-1 p-2 bg-white/60 dark:bg-black/20 rounded text-[10px] whitespace-pre-wrap max-h-40 overflow-y-auto font-mono">
                {doc.ocr_text}
              </pre>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export function TripletComparisonView({ triplet, onClose }) {
  const [lr, setLr]           = useState(null)
  const [pod, setPod]         = useState(null)
  const [invoice, setInvoice] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchDocs() {
      setLoading(true)
      try {
        const [lrRes, podRes, invRes] = await Promise.allSettled([
          api.getDocument(triplet.lr_id),
          api.getDocument(triplet.pod_id),
          api.getDocument(triplet.invoice_id),
        ])
        if (lrRes.status  === 'fulfilled') setLr(lrRes.value.data)
        if (podRes.status === 'fulfilled') setPod(podRes.value.data)
        if (invRes.status === 'fulfilled') setInvoice(invRes.value.data)
      } finally {
        setLoading(false)
      }
    }
    fetchDocs()
  }, [triplet])

  const fieldMatches = triplet.field_matches || {}
  const lrEnt      = lr?.entities      || {}
  const podEnt     = pod?.entities     || {}
  const invoiceEnt = invoice?.entities || {}

  const allFields = Array.from(new Set([
    ...Object.keys(lrEnt),
    ...Object.keys(podEnt),
    ...Object.keys(invoiceEnt),
  ])).filter(f => FIELD_LABELS[f])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="bg-background rounded-xl shadow-2xl w-full max-w-5xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <div>
            <h2 className="text-lg font-bold">Triplet Comparison</h2>
            <p className="text-xs text-muted-foreground">
              ID: {triplet.id.slice(0, 16)}… &nbsp;·&nbsp;
              Confidence: <span className="font-semibold">{Math.round(triplet.confidence * 100)}%</span> &nbsp;·&nbsp;
              Match Score: <span className="font-semibold">{Math.round(triplet.match_score * 100)}%</span>
            </p>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-5 w-5" />
          </Button>
        </div>

        <div className="overflow-y-auto flex-1 p-6 space-y-6">
          {loading ? (
            <div className="flex items-center justify-center py-16 text-muted-foreground">
              <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full mr-3" />
              Loading documents…
            </div>
          ) : (
            <>
              {/* Document Panels */}
              <div className="flex gap-3">
                <DocPanel label="LR"      doc={lr}      color={DOC_COLORS.LR} />
                <DocPanel label="POD"     doc={pod}     color={DOC_COLORS.POD} />
                <DocPanel label="Invoice" doc={invoice} color={DOC_COLORS.INVOICE} />
              </div>

              {/* Field Comparison Table */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Field-by-Field Comparison</CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b bg-muted/50">
                          <th className="text-left px-4 py-2 font-medium text-muted-foreground w-32">Field</th>
                          <th className={`text-left px-4 py-2 font-medium ${DOC_COLORS.LR.text}`}>LR</th>
                          <th className={`text-left px-4 py-2 font-medium ${DOC_COLORS.POD.text}`}>POD</th>
                          <th className={`text-left px-4 py-2 font-medium ${DOC_COLORS.INVOICE.text}`}>Invoice</th>
                          <th className="text-center px-4 py-2 font-medium text-muted-foreground">Match</th>
                          <th className="text-center px-4 py-2 font-medium text-muted-foreground">Score</th>
                        </tr>
                      </thead>
                      <tbody>
                        {allFields.length === 0 ? (
                          <tr>
                            <td colSpan={6} className="text-center py-8 text-muted-foreground">
                              No entity data extracted yet
                            </td>
                          </tr>
                        ) : allFields.map(field => {
                          const fm    = fieldMatches[field] || {}
                          const score = fm.score
                          const lrVal  = lrEnt[field]      ?? '–'
                          const podVal = podEnt[field]     ?? '–'
                          const invVal = invoiceEnt[field] ?? '–'

                          const rowClass = score !== undefined
                            ? score >= 0.9 ? 'bg-green-50/50 dark:bg-green-950/20'
                            : score >= 0.6 ? 'bg-yellow-50/50 dark:bg-yellow-950/20'
                            : 'bg-red-50/50 dark:bg-red-950/20'
                            : ''

                          return (
                            <tr key={field} className={`border-b last:border-0 ${rowClass}`}>
                              <td className="px-4 py-2 font-medium text-muted-foreground">
                                {FIELD_LABELS[field] || field}
                              </td>
                              <td className="px-4 py-2 font-mono text-xs">{String(lrVal)}</td>
                              <td className="px-4 py-2 font-mono text-xs">{String(podVal)}</td>
                              <td className="px-4 py-2 font-mono text-xs">{String(invVal)}</td>
                              <td className="px-4 py-2 text-center">
                                <MatchDot score={score} />
                              </td>
                              <td className="px-4 py-2 text-center text-xs font-medium">
                                {score !== undefined ? `${Math.round(score * 100)}%` : '–'}
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>

              {/* Validation Results */}
              {triplet.validation_results?.length > 0 && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">Validation Rules</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    {triplet.validation_results.map((v, i) => (
                      <div key={i} className="flex items-start gap-3 p-2 rounded bg-muted/40">
                        {v.passed
                          ? <CheckCircle2 className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                          : <XCircle      className="h-4 w-4 text-red-500   mt-0.5 flex-shrink-0" />
                        }
                        <div className="min-w-0">
                          <p className="text-xs font-semibold">{v.rule}</p>
                          <p className="text-xs text-muted-foreground">{v.message}</p>
                        </div>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}

              {/* AI Explanation */}
              {triplet.ai_explanation && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">AI Audit Explanation</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground leading-relaxed">{triplet.ai_explanation}</p>
                  </CardContent>
                </Card>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
