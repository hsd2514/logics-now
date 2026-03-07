import React from 'react'
import { FileText, CheckCircle, AlertTriangle, Clock, TrendingUp, Zap, Timer } from 'lucide-react'
import { Card, CardContent } from './ui/card'

export function StatsCards({ stats }) {
  const cards = [
    {
      title: 'Total Documents',
      value: stats?.documents?.total || 0,
      icon: FileText,
      color: 'text-blue-600 dark:text-blue-400',
      bg: 'bg-blue-100/50 dark:bg-blue-900/20',
    },
    {
      title: 'Matched Triplets',
      value: stats?.triplets?.total || 0,
      icon: CheckCircle,
      color: 'text-green-600 dark:text-green-400',
      bg: 'bg-green-100/50 dark:bg-green-900/20',
    },
    {
      title: 'Pending Review',
      value: stats?.triplets?.by_status?.REVIEW || 0,
      icon: Clock,
      color: 'text-yellow-600 dark:text-yellow-400',
      bg: 'bg-yellow-100/50 dark:bg-yellow-900/20',
    },
    {
      title: 'Fraud Alerts',
      value: stats?.fraud?.open_alerts || 0,
      icon: AlertTriangle,
      color: 'text-red-600 dark:text-red-400',
      bg: 'bg-red-100/50 dark:bg-red-900/20',
    },
    {
      title: 'Avg Confidence',
      value: `${stats?.triplets?.avg_confidence || 0}%`,
      icon: TrendingUp,
      color: 'text-purple-600 dark:text-purple-400',
      bg: 'bg-purple-100/50 dark:bg-purple-900/20',
    },
    {
      title: 'Automation Rate',
      value: `${stats?.triplets?.automation_rate || 0}%`,
      icon: Zap,
      color: 'text-indigo-600 dark:text-indigo-400',
      bg: 'bg-indigo-100/50 dark:bg-indigo-900/20',
    },
    {
      title: 'Avg Proc Time',
      value: `${(((stats?.efficiency?.avg_processing_time_ms || 0) / 1000).toFixed(2))}s`,
      icon: Timer,
      color: 'text-teal-600 dark:text-teal-400',
      bg: 'bg-teal-100/50 dark:bg-teal-900/20',
    },
  ]

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-7 gap-4">
      {cards.map((card, idx) => {
        const Icon = card.icon
        const isFraudCard = card.title === 'Fraud Alerts'
        const fraudCount = Number(stats?.fraud?.open_alerts || 0)
        return (
          <Card key={idx} className={isFraudCard && fraudCount > 0 ? 'ring-1 ring-red-300 animate-pulse' : ''}>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg ${card.bg}`}>
                  <Icon className={`h-5 w-5 ${card.color}`} />
                </div>
                <div>
                  <p className="text-2xl font-bold">{card.value}</p>
                  <p className="text-xs text-muted-foreground">{card.title}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
