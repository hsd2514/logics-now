import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'

export function AttentionHeatmap({ attentionMap, documentType }) {
  if (!attentionMap || attentionMap.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        No attention data available
      </div>
    )
  }

  const getScoreColor = (score) => {
    if (score >= 0.8) return 'bg-green-500/30 border-green-500'
    if (score >= 0.5) return 'bg-yellow-500/30 border-yellow-500'
    return 'bg-red-500/30 border-red-500'
  }

  const filteredRegions = documentType 
    ? attentionMap.filter(r => r.document_type === documentType)
    : attentionMap

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Explainable AI - Attention Heatmap</CardTitle>
        <p className="text-xs text-muted-foreground">
          Shows which regions of the documents contributed to the match
        </p>
      </CardHeader>
      <CardContent>
        <div className="relative bg-muted/50 rounded-lg p-4 min-h-[200px]">
          {/* Document visualization placeholder */}
          <div className="absolute inset-4 border-2 border-dashed border-muted-foreground/20 rounded">
            {filteredRegions.map((region, idx) => (
              <div
                key={idx}
                className={`absolute border-2 rounded transition-all ${getScoreColor(region.score)}`}
                style={{
                  left: `${(region.x / 600) * 100}%`,
                  top: `${(region.y / 800) * 100}%`,
                  width: `${Math.max((region.width / 600) * 100, 15)}%`,
                  height: `${Math.max((region.height / 800) * 100, 8)}%`,
                }}
                title={`${region.field}: ${Math.round(region.score * 100)}%`}
              >
                <div className="absolute -top-5 left-0 text-xs font-medium whitespace-nowrap">
                  {region.field}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-4 mt-4 text-xs">
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded bg-green-500/50 border border-green-500" />
            <span>High Match (80%+)</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded bg-yellow-500/50 border border-yellow-500" />
            <span>Partial (50-80%)</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded bg-red-500/50 border border-red-500" />
            <span>Low (&lt;50%)</span>
          </div>
        </div>

        {/* Region Details */}
        <div className="mt-4 space-y-2">
          {filteredRegions.map((region, idx) => (
            <div key={idx} className="flex items-center justify-between p-2 bg-muted rounded text-sm">
              <div className="flex items-center gap-2">
                <Badge variant="outline">{region.document_type}</Badge>
                <span className="font-medium">{region.field}</span>
              </div>
              <div className={`font-medium ${
                region.score >= 0.8 ? 'text-green-600' :
                region.score >= 0.5 ? 'text-yellow-600' : 'text-red-600'
              }`}>
                {Math.round(region.score * 100)}%
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
