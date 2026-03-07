import React, { useState, useEffect } from 'react'
import { AlertTriangle, ShieldAlert, TrendingUp, CheckCircle, XCircle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Badge } from './ui/badge'
import { ScrollArea } from './ui/scroll-area'
import * as api from '../services/api'

export function FraudAlertPanel() {
  const [alerts, setAlerts] = useState([])
  const [predictiveAlerts, setPredictiveAlerts] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchAlerts()
    fetchPredictiveAlerts()
  }, [])

  const fetchAlerts = async () => {
    try {
      setLoading(true)
      const response = await api.getFraudAlerts({ status: 'OPEN' })
      setAlerts(response.data.alerts)
    } catch (err) {
      console.error('Failed to fetch alerts:', err)
    } finally {
      setLoading(false)
    }
  }

  const fetchPredictiveAlerts = async () => {
    try {
      const response = await api.getPredictiveAlerts()
      setPredictiveAlerts(response.data)
    } catch (err) {
      console.error('Failed to fetch predictive alerts:', err)
    }
  }

  const handleDismiss = async (alertId) => {
    const reviewer = window.prompt("Enter reviewer name for audit log:")
    if (!reviewer) return

    try {
      await api.dismissAlert(alertId, { user_id: reviewer, notes: "Dismissed via dashboard" })
      fetchAlerts()
    } catch (err) {
      console.error('Failed to dismiss alert:', err)
    }
  }

  const handleConfirm = async (alertId) => {
    const reviewer = window.prompt("Enter reviewer name for audit log:")
    if (!reviewer) return

    try {
      await api.confirmAlert(alertId, { user_id: reviewer, notes: "Confirmed via dashboard" })
      fetchAlerts()
    } catch (err) {
      console.error('Failed to confirm alert:', err)
    }
  }

  const getAlertTypeConfig = (type) => {
    const configs = {
      DUPLICATE: { icon: AlertTriangle, color: 'text-red-600 dark:text-red-400', bg: 'bg-red-100/50 dark:bg-red-950/20' },
      AMOUNT_ANOMALY: { icon: TrendingUp, color: 'text-orange-600 dark:text-orange-400', bg: 'bg-orange-100/50 dark:bg-orange-950/20' },
      VENDOR_ANOMALY: { icon: ShieldAlert, color: 'text-yellow-600 dark:text-yellow-400', bg: 'bg-yellow-100/50 dark:bg-yellow-950/20' },
      PREDICTED: { icon: TrendingUp, color: 'text-purple-600 dark:text-purple-400', bg: 'bg-purple-100/50 dark:bg-purple-950/20' },
    }
    return configs[type] || configs.AMOUNT_ANOMALY
  }

  const getRiskBadge = (score) => {
    if (score >= 0.8) return <Badge variant="destructive">Critical</Badge>
    if (score >= 0.6) return <Badge variant="warning">High</Badge>
    if (score >= 0.4) return <Badge variant="secondary">Medium</Badge>
    return <Badge variant="outline">Low</Badge>
  }

  const handleExport = async (format) => {
    try {
      const res = await api.exportFraudAlerts(format)
      const blobUrl = URL.createObjectURL(res.data)
      const a = document.createElement('a')
      a.href = blobUrl
      a.download = `fraud_alerts.${format}`
      a.click()
      URL.revokeObjectURL(blobUrl)
    } catch (err) {
      console.error('Failed to export fraud alerts:', err)
    }
  }

  return (
    <Card className="h-full">
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <CardTitle className="flex items-center gap-2">
            <ShieldAlert className="h-5 w-5 text-red-500" />
            Fraud Alerts
            {alerts.length > 0 && (
              <Badge variant="destructive" className="ml-auto">{alerts.length}</Badge>
            )}
          </CardTitle>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => handleExport('csv')}>Export CSV</Button>
            <Button variant="outline" size="sm" onClick={() => handleExport('pdf')}>Export PDF</Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[400px] pr-4">
          {/* Active Alerts */}
          {alerts.length === 0 && predictiveAlerts.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <ShieldAlert className="h-12 w-12 mx-auto mb-2 opacity-20" />
              <p>No active fraud alerts</p>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Regular Alerts */}
              {alerts.map(alert => {
                const config = getAlertTypeConfig(alert.alert_type)
                const Icon = config.icon

                return (
                  <div key={alert.id} className={`p-4 rounded-lg ${config.bg}`}>
                    <div className="flex items-start gap-3">
                      <Icon className={`h-5 w-5 ${config.color} mt-0.5`} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium text-sm">{alert.alert_type.replace('_', ' ')}</span>
                          {getRiskBadge(alert.risk_score)}
                        </div>
                        <p className="text-sm text-muted-foreground mb-2">
                          {alert.ai_reasoning || 'Suspicious activity detected'}
                        </p>
                        <div className="text-xs text-muted-foreground mb-2">
                          Triplet: {alert.triplet_id.slice(0, 8)}
                        </div>
                        <div className="flex gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleDismiss(alert.id)}
                          >
                            <XCircle className="h-3 w-3 mr-1" />
                            Dismiss
                          </Button>
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={() => handleConfirm(alert.id)}
                          >
                            <CheckCircle className="h-3 w-3 mr-1" />
                            Confirm Fraud
                          </Button>
                        </div>
                      </div>
                    </div>
                  </div>
                )
              })}

              {/* Predictive Alerts (Novel Feature) */}
              {predictiveAlerts.length > 0 && (
                <>
                  <div className="text-sm font-medium text-muted-foreground pt-4 border-t">
                    Predictive Alerts (AI)
                  </div>
                  {predictiveAlerts.map((alert, idx) => (
                    <div key={idx} className="p-4 rounded-lg bg-purple-100/50 dark:bg-purple-900/20">
                      <div className="flex items-start gap-3">
                        <TrendingUp className="h-5 w-5 text-purple-500 mt-0.5" />
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-medium text-sm">{alert.vendor_name}</span>
                            {getRiskBadge(alert.risk_score)}
                          </div>
                          <p className="text-sm text-muted-foreground">
                            {alert.reasoning}
                          </p>
                          <p className="text-xs text-purple-600 dark:text-purple-400 mt-2">
                            {alert.recommended_action}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </>
              )}
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
