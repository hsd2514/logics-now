import React from 'react'
import { cn } from '../lib/utils'

export function Skeleton({ className, ...props }) {
  return (
    <div
      className={cn('animate-pulse rounded-md bg-muted', className)}
      {...props}
    />
  )
}

export function CardSkeleton() {
  return (
    <div className="border rounded-xl p-4 space-y-3 bg-card">
      <div className="flex justify-between items-center">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-5 w-20 rounded-full" />
      </div>
      <div className="grid grid-cols-3 gap-2">
        <Skeleton className="h-12 rounded" />
        <Skeleton className="h-12 rounded" />
        <Skeleton className="h-12 rounded" />
      </div>
      <Skeleton className="h-2 w-full rounded-full" />
      <div className="grid grid-cols-2 gap-2">
        <Skeleton className="h-8 rounded" />
        <Skeleton className="h-8 rounded" />
      </div>
      <div className="flex gap-2">
        <Skeleton className="h-8 w-20 rounded" />
        <Skeleton className="h-8 w-20 rounded" />
      </div>
    </div>
  )
}

export function StatsCardSkeleton() {
  return (
    <div className="border rounded-xl p-4 bg-card flex items-center gap-3">
      <Skeleton className="h-10 w-10 rounded-lg flex-shrink-0" />
      <div className="space-y-1 flex-1">
        <Skeleton className="h-6 w-16" />
        <Skeleton className="h-3 w-24" />
      </div>
    </div>
  )
}

export function TableRowSkeleton({ cols = 4 }) {
  return (
    <tr className="border-b">
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <Skeleton className="h-4 w-full max-w-[120px]" />
        </td>
      ))}
    </tr>
  )
}
