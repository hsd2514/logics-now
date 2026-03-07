import React, { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'

const DOC_TYPES = ['LR', 'POD', 'INVOICE']

const SCORE_STYLE = (score) => {
  if (score >= 0.8) return { box: 'border-green-500 bg-green-500/20', text: 'text-green-600 dark:text-green-400', label: 'High' }
  if (score >= 0.5) return { box: 'border-yellow-500 bg-yellow-500/20', text: 'text-yellow-600 dark:text-yellow-400', label: 'Mid' }
  return { box: 'border-red-500 bg-red-500/20', text: 'text-red-600 dark:text-red-400', label: 'Low' }
}

/**
 * Resolve normalised [0,1] coords for a region.
 * Prefers x_norm / y_norm / w_norm / h_norm stored by the backend.
 * Falls back to dividing raw pixels by doc_width/doc_height if present.
 * Last resort: returns null (region cannot be positioned).
 */
function resolveNorm(region) {
  // Best case: backend already normalised
  if (
    region.x_norm != null && region.y_norm != null &&
    region.w_norm != null && region.h_norm != null
  ) {
    return {
      x: region.x_norm,
      y: region.y_norm,
      w: region.w_norm,
      h: region.h_norm,
    }
  }

  // Second best: raw pixels + stored doc dimensions
  if (region.doc_width > 0 && region.doc_height > 0) {
    return {
      x: region.x / region.doc_width,
      y: region.y / region.doc_height,
      w: Math.max(region.width / region.doc_width, 0.02),
      h: Math.max(region.height / region.doc_height, 0.02),
    }
  }

  // Cannot render — no dimension info available
  return null
}

function DocumentCanvas({ regions, docType }) {
  const positionable = regions
    .map(r => ({ ...r, norm: resolveNorm(r) }))
    .filter(r => r.norm !== null)

  const noPosition = regions.filter(r => resolveNorm(r) === null)

  return (
    <div className="space-y-2">
      {/* Heatmap canvas */}
      <div
        className="relative w-full bg-muted/40 border border-dashed border-muted-foreground/30 rounded-lg overflow-hidden"
        style={{ paddingBottom: '133%' /* 3:4 aspect → portrait document */ }}
        aria-label={`Attention heatmap for ${docType}`}
      >
        {/* Document page lines (decorative) */}
        {[20, 35, 50, 65, 80].map(pct => (
          <div
            key={pct}
            className="absolute left-4 right-4 h-px bg-muted-foreground/10"
            style={{ top: `${pct}%` }}
          />
        ))}

        {positionable.map((region, idx) => {
          const { x, y, w, h } = region.norm
          const style = SCORE_STYLE(region.score)
          return (
            <div
              key={idx}
              className={`absolute border-2 rounded transition-all cursor-default ${style.box}`}
              style={{
                left: `${(x * 100).toFixed(2)}%`,
                top: `${(y * 100).toFixed(2)}%`,
                width: `${(w * 100).toFixed(2)}%`,
                height: `${(h * 100).toFixed(2)}%`,
              }}
              title={`${region.field} · ${Math.round(region.score * 100)}% match`}
            >
              <span
                className={`absolute -top-5 left-0 text-[10px] font-semibold whitespace-nowrap ${style.text}`}
              >
                {region.field}
              </span>
            </div>
          )
        })}

        {positionable.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center text-xs text-muted-foreground">
            No positioned regions for {docType}
          </div>
        )}
      </div>

      {/* Regions without position info — show as list */}
      {noPosition.length > 0 && (
        <p className="text-xs text-muted-foreground italic">
          {noPosition.length} region(s) lack coordinate data (HTML/text documents).
        </p>
      )}
    </div>
  )
}

export function AttentionHeatmap({ attentionMap }) {
  const [activeDoc, setActiveDoc] = useState('LR')

  if (!attentionMap || attentionMap.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground text-sm">
        No attention data available for this triplet.
      </div>
    )
  }

  const regionsByDoc = Object.fromEntries(
    DOC_TYPES.map(dt => [dt, attentionMap.filter(r => r.document_type === dt)])
  )

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Explainable AI — Attention Heatmap</CardTitle>
          <Badge variant="outline" className="text-xs">Document-grounded</Badge>
        </div>
        <p className="text-xs text-muted-foreground">
          Highlighted regions show where each matched field was found in the document.
          Coordinates are derived from actual OCR bounding boxes.
        </p>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Doc-type tabs */}
        <div className="flex gap-1">
          {DOC_TYPES.map(dt => (
            <button
              key={dt}
              onClick={() => setActiveDoc(dt)}
              className={`px-3 py-1 rounded text-xs font-medium transition-colors ${activeDoc === dt
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground hover:bg-muted/80'
                }`}
            >
              {dt}
              <span className="ml-1 opacity-60">({regionsByDoc[dt].length})</span>
            </button>
          ))}
        </div>

        {/* Canvas */}
        <DocumentCanvas regions={regionsByDoc[activeDoc]} docType={activeDoc} />

        {/* Legend */}
        <div className="flex items-center gap-4 text-xs flex-wrap">
          {[
            { label: 'High match (80%+)', cls: 'bg-green-500/40 border-green-500' },
            { label: 'Partial (50–80%)', cls: 'bg-yellow-500/40 border-yellow-500' },
            { label: 'Low (<50%)', cls: 'bg-red-500/40 border-red-500' },
          ].map(({ label, cls }) => (
            <div key={label} className="flex items-center gap-1">
              <div className={`w-3 h-3 rounded border-2 ${cls}`} />
              <span>{label}</span>
            </div>
          ))}
        </div>

        {/* Field table */}
        <div className="space-y-1 max-h-48 overflow-y-auto">
          {regionsByDoc[activeDoc].map((region, idx) => {
            const style = SCORE_STYLE(region.score)
            return (
              <div
                key={idx}
                className="flex items-center justify-between px-2 py-1 bg-muted rounded text-sm"
              >
                <div className="flex items-center gap-2">
                  <span className="font-medium capitalize">{region.field.replace('_', ' ')}</span>
                  {region.x_norm != null
                    ? <span className="text-xs text-muted-foreground">({(region.x_norm * 100).toFixed(1)}%, {(region.y_norm * 100).toFixed(1)}%)</span>
                    : <span className="text-xs text-muted-foreground italic">no coords</span>
                  }
                </div>
                <span className={`font-semibold ${style.text}`}>
                  {Math.round(region.score * 100)}%
                </span>
              </div>
            )
          })}
          {regionsByDoc[activeDoc].length === 0 && (
            <p className="text-xs text-muted-foreground text-center py-2">
              No matched fields for {activeDoc}.
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
