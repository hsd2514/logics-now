import React from 'react'
import { FileText, CheckCircle, XCircle, AlertTriangle, Eye, MessageSquare, Download } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from './ui/card'
import { Button } from './ui/button'
import { Badge } from './ui/badge'
import { Progress } from './ui/progress'

export function TripletCard({ triplet, onApprove, onReject, onViewDetails, onChat, onExportAudit }) {
  const confidenceBand = triplet.confidence >= 0.9 ? 'border-l-4 border-l-green-500' :
    triplet.confidence >= 0.7 ? 'border-l-4 border-l-amber-500' : 'border-l-4 border-l-red-500'

  const getStatusBadge = (status) => {
    const statusConfig = {
      AUTO_APPROVED: { variant: 'success', label: 'Auto Approved' },
      APPROVED: { variant: 'success', label: 'Approved' },
      REJECTED: { variant: 'destructive', label: 'Rejected' },
      REVIEW: { variant: 'warning', label: 'Needs Review' },
      PENDING: { variant: 'secondary', label: 'Pending' },
    }
    const config = statusConfig[status] || statusConfig.PENDING
    return <Badge variant={config.variant}>{config.label}</Badge>
  }

  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.9) return 'bg-green-500'
    if (confidence >= 0.7) return 'bg-yellow-500'
    return 'bg-red-500'
  }

  const confidencePercent = Math.round(triplet.confidence * 100)

  return (
    <Card className={`overflow-hidden ${confidenceBand}`}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-medium">
            Triplet #{triplet.id.slice(0, 8)}
          </CardTitle>
          {getStatusBadge(triplet.status)}
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Document References */}
        <div className="grid grid-cols-3 gap-2 text-sm">
          <div className="flex items-center gap-1 p-2 bg-blue-100/50 dark:bg-blue-900/20 rounded">
            <FileText className="h-4 w-4 text-blue-600 dark:text-blue-400" />
            <div>
              <div className="text-xs text-muted-foreground">LR</div>
              <div className="font-mono text-xs">{triplet.lr_id.slice(0, 8)}</div>
            </div>
          </div>
          <div className="flex items-center gap-1 p-2 bg-green-100/50 dark:bg-green-900/20 rounded">
            <FileText className="h-4 w-4 text-green-600 dark:text-green-400" />
            <div>
              <div className="text-xs text-muted-foreground">POD</div>
              <div className="font-mono text-xs">{triplet.pod_id.slice(0, 8)}</div>
            </div>
          </div>
          <div className="flex items-center gap-1 p-2 bg-purple-100/50 dark:bg-purple-900/20 rounded">
            <FileText className="h-4 w-4 text-purple-600 dark:text-purple-400" />
            <div>
              <div className="text-xs text-muted-foreground">Invoice</div>
              <div className="font-mono text-xs">{triplet.invoice_id.slice(0, 8)}</div>
            </div>
          </div>
        </div>

        {/* Confidence Score */}
        <div className="space-y-1">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Confidence</span>
            <span className="font-medium">{confidencePercent}%</span>
          </div>
          <div className="relative h-2 rounded-full bg-muted overflow-hidden">
            <div
              className={`h-full transition-all ${getConfidenceColor(triplet.confidence)}`}
              style={{ width: `${confidencePercent}%` }}
            />
          </div>
        </div>

        {/* Score Breakdown */}
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="flex justify-between p-2 bg-muted rounded">
            <span>Match Score</span>
            <span className="font-medium">{Math.round(triplet.match_score * 100)}%</span>
          </div>
          <div className="flex justify-between p-2 bg-muted rounded">
            <span>OCR Accuracy</span>
            <span className="font-medium">{Math.round((triplet.ocr_accuracy || 0.9) * 100)}%</span>
          </div>
        </div>

        {/* AI Explanation */}
        {triplet.ai_explanation && (
          <div className="p-3 bg-muted/50 rounded text-sm">
            <div className="text-xs font-medium text-muted-foreground mb-1">AI Analysis</div>
            <p className="text-xs line-clamp-2">{triplet.ai_explanation}</p>
          </div>
        )}
      </CardContent>

      <CardFooter className="gap-2 pt-2">
        <Button variant="outline" size="sm" onClick={() => onViewDetails?.(triplet)}>
          <Eye className="h-4 w-4 mr-1" />
          Details
        </Button>
        <Button variant="outline" size="sm" onClick={() => onChat?.(triplet)}>
          <MessageSquare className="h-4 w-4 mr-1" />
          Chat
        </Button>
        <Button variant="outline" size="sm" onClick={() => onExportAudit?.(triplet)}>
          <Download className="h-4 w-4 mr-1" />
          Audit
        </Button>
        {triplet.status === 'REVIEW' && (
          <>
            <Button
              variant="default"
              size="sm"
              className="ml-auto"
              onClick={() => onApprove?.(triplet.id)}
            >
              <CheckCircle className="h-4 w-4 mr-1" />
              Approve
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={() => onReject?.(triplet.id)}
            >
              <XCircle className="h-4 w-4 mr-1" />
              Reject
            </Button>
          </>
        )}
      </CardFooter>
    </Card>
  )
}
