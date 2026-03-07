import React, { useMemo, useState } from 'react'
import { Button } from './ui/button'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'
import * as api from '../services/api'

function nowLabel() {
  return new Date().toLocaleTimeString()
}

export function AdminDemoDashboard({ onRefresh }) {
  const [runningId, setRunningId] = useState(null)
  const [results, setResults] = useState({})
  const [lastRun, setLastRun] = useState(null)

  const actions = useMemo(
    () => [
      {
        id: 'demo_clean',
        label: 'Generate Clean Demo Shipment',
        run: () => api.generateDemo(false),
      },
      {
        id: 'demo_fraud',
        label: 'Generate Fraud Demo Shipment',
        run: () => api.generateDemo(true),
      },
      {
        id: 'demo_partial',
        label: 'Generate Partial Delivery Demo',
        run: () => api.generateDemo(false, true),
      },
      {
        id: 'match',
        label: 'Run Matching Pipeline',
        run: () => api.runMatching(),
      },
      {
        id: 'stats',
        label: 'Load Dashboard Stats',
        run: () => api.getStats(),
      },
      {
        id: 'fraud_predictions',
        label: 'Load Fraud Predictions',
        run: () => api.getPredictiveAlerts(),
      },
      {
        id: 'vendors',
        label: 'Refresh Vendor Profiles',
        run: () => api.refreshVendorProfiles(),
      },
      {
        id: 'vendor_analytics',
        label: 'Load Vendor Analytics',
        run: () => api.getVendorAnalytics(),
      },
      {
        id: 'vendor_profiles',
        label: 'Load Vendor Profiles (Risk Sorted)',
        run: () => api.getVendorProfiles({ limit: 20, sort_by: 'risk_score' }),
      },
      {
        id: 'vendor_details',
        label: 'Vendor Details Deep Dive',
        run: async () => {
          const profilesRes = await api.getVendorProfiles({ limit: 1, sort_by: 'risk_score' })
          const first = profilesRes?.data?.profiles?.[0]
          if (!first?.vendor_name) throw new Error('No vendor profile available yet')
          return api.getVendorDetails(first.vendor_name)
        },
      },
      {
        id: 'nl_query',
        label: 'Run NL Query',
        run: () => api.nlQuerySync('Show high risk vendors and pending review triplets'),
      },
      {
        id: 'contracts_crud',
        label: 'Contract Rate CRUD Demo',
        run: async () => {
          const suffix = Date.now()
          const vendor = `DemoVendor-${suffix}`
          const created = await api.createContractRate({
            vendor_name: vendor,
            origin: 'Mumbai',
            destination: 'Hyderabad',
            base_rate: 12000,
            fuel_surcharge: 700,
            detention_rate: 200,
            distance_rate: 500,
            is_active: true,
          })
          const id = created?.data?.id
          if (!id) throw new Error('Contract rate create did not return id')
          await api.updateContractRate(id, { base_rate: 12500 })
          await api.getContractRates({ vendor_name: vendor })
          await api.deleteContractRate(id)
          return { data: { id } }
        },
      },
      {
        id: 'exports',
        label: 'Triplet Export (CSV/PDF) Smoke Test',
        run: async () => {
          await api.exportTriplets('csv')
          await api.exportTriplets('pdf')
          return { data: { ok: true } }
        },
      },
    ],
    []
  )

  const runOne = async (action) => {
    setRunningId(action.id)
    try {
      const res = await action.run()
      setResults((prev) => ({
        ...prev,
        [action.id]: {
          status: 'ok',
          at: nowLabel(),
          message: res?.data?.message || 'Success',
        },
      }))
    } catch (err) {
      setResults((prev) => ({
        ...prev,
        [action.id]: {
          status: 'error',
          at: nowLabel(),
          message: err?.response?.data?.detail || err?.message || 'Failed',
        },
      }))
    } finally {
      setRunningId(null)
      setLastRun(nowLabel())
      onRefresh?.()
    }
  }

  const runAll = async () => {
    for (const action of actions) {
      // sequential to keep backend load predictable for demo runs
      // eslint-disable-next-line no-await-in-loop
      await runOne(action)
    }
  }

  const statusBadge = (id) => {
    const r = results[id]
    if (!r) return <Badge variant="outline">Not Run</Badge>
    if (r.status === 'ok') return <Badge className="bg-green-600 text-white">Pass</Badge>
    return <Badge variant="destructive">Fail</Badge>
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Admin Demo Dashboard</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col sm:flex-row gap-2">
            <Button onClick={runAll} disabled={!!runningId}>
              {runningId ? `Running: ${runningId}` : 'Run All Features'}
            </Button>
            <Button variant="outline" onClick={onRefresh}>
              Refresh App Data
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            Use this panel to demo each feature quickly. Last run: {lastRun || 'never'}
          </p>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {actions.map((action) => {
          const r = results[action.id]
          const busy = runningId === action.id
          return (
            <Card key={action.id} className="min-w-0">
              <CardContent className="pt-6 space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="font-medium">{action.label}</div>
                  {statusBadge(action.id)}
                </div>
                <div className="flex items-center gap-2">
                  <Button size="sm" onClick={() => runOne(action)} disabled={!!runningId}>
                    {busy ? 'Running...' : 'Run'}
                  </Button>
                  <span className="text-xs text-muted-foreground">{r?.at || '-'}</span>
                </div>
                {r?.message ? (
                  <div className="text-xs text-muted-foreground break-words">{r.message}</div>
                ) : null}
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}

export default AdminDemoDashboard
