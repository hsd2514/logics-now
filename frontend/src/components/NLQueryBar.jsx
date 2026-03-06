import React, { useState } from 'react'
import { Search, Sparkles, Loader2 } from 'lucide-react'
import { Input } from './ui/input'
import { Button } from './ui/button'
import { Badge } from './ui/badge'
import * as api from '../services/api'

export function NLQueryBar({ onFiltersApplied }) {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [filters, setFilters] = useState(null)
  const [error, setError] = useState(null)

  const handleSearch = async () => {
    if (!query.trim()) return
    
    setLoading(true)
    setError(null)
    
    try {
      const response = await api.nlQuerySync(query)
      const parsedFilters = response.data.filters
      
      if (parsedFilters.error) {
        setError(parsedFilters.error)
        setFilters(null)
      } else {
        setFilters(parsedFilters)
        setError(null)
        onFiltersApplied?.(parsedFilters)
      }
    } catch (err) {
      setError('Failed to parse query')
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  const clearFilters = () => {
    setFilters(null)
    setQuery('')
    onFiltersApplied?.({})
  }

  const exampleQueries = [
    "Show invoices above 50000 from last week",
    "Pending triplets with high risk",
    "Invoices from ABC Transport",
  ]

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            className="pl-10 pr-10"
            placeholder="Ask in natural language... e.g., 'Show invoices above 50k from last week'"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <Sparkles className="absolute right-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-purple-500" />
        </div>
        <Button onClick={handleSearch} disabled={loading || !query.trim()}>
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Search'}
        </Button>
      </div>

      {/* Example Queries */}
      {!filters && !error && (
        <div className="flex flex-wrap gap-1">
          <span className="text-xs text-muted-foreground">Try:</span>
          {exampleQueries.map((eq, idx) => (
            <button
              key={idx}
              className="text-xs text-primary hover:underline"
              onClick={() => setQuery(eq)}
            >
              "{eq}"
            </button>
          ))}
        </div>
      )}

      {/* Applied Filters */}
      {filters && Object.keys(filters).length > 0 && (
        <div className="flex flex-wrap items-center gap-2 p-2 bg-muted rounded">
          <span className="text-xs font-medium">Filters:</span>
          {Object.entries(filters).map(([key, value]) => (
            <Badge key={key} variant="secondary" className="text-xs">
              {key}: {String(value)}
            </Badge>
          ))}
          <Button variant="ghost" size="sm" className="h-6 text-xs ml-auto" onClick={clearFilters}>
            Clear
          </Button>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="text-sm text-destructive">
          {error}
        </div>
      )}
    </div>
  )
}
