import React, { useMemo } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend, LineChart, Line, AreaChart, Area,
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { TrendingUp, PieChart as PieIcon, BarChart2, Activity } from 'lucide-react'

const COLORS = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#a855f7', '#06b6d4']

const STATUS_COLORS = {
  AUTO_APPROVED: '#22c55e',
  APPROVED:      '#3b82f6',
  REVIEW:        '#f59e0b',
  PENDING:       '#94a3b8',
  REJECTED:      '#ef4444',
}

const FRAUD_COLORS = {
  DUPLICATE:      '#ef4444',
  AMOUNT_ANOMALY: '#f97316',
  VENDOR_ANOMALY: '#eab308',
  FREQUENCY:      '#a855f7',
  PREDICTED:      '#06b6d4',
}

/* Confidence histogram — bucket triplets into bands */
function buildConfidenceBuckets(triplets) {
  const buckets = [
    { label: '0–50%',   min: 0,    max: 0.50, count: 0 },
    { label: '50–70%',  min: 0.50, max: 0.70, count: 0 },
    { label: '70–85%',  min: 0.70, max: 0.85, count: 0 },
    { label: '85–95%',  min: 0.85, max: 0.95, count: 0 },
    { label: '95–100%', min: 0.95, max: 1.01, count: 0 },
  ]
  triplets.forEach(t => {
    const c = t.confidence ?? 0
    const b = buckets.find(bk => c >= bk.min && c < bk.max)
    if (b) b.count++
  })
  return buckets.map(({ label, count }) => ({ label, count }))
}

/* Status breakdown */
function buildStatusData(triplets) {
  const counts = {}
  triplets.forEach(t => { counts[t.status] = (counts[t.status] || 0) + 1 })
  return Object.entries(counts).map(([status, count]) => ({ status, count }))
}

/* Fraud type breakdown */
function buildFraudData(fraudAlerts) {
  const counts = {}
  fraudAlerts.forEach(a => { counts[a.alert_type] = (counts[a.alert_type] || 0) + 1 })
  return Object.entries(counts).map(([type, value]) => ({ type, value }))
}

/* Synthetic trend — group triplets created by day */
function buildTrends(triplets) {
  const byDay = {}
  triplets.forEach(t => {
    const day = (t.created_at || '').slice(0, 10) || 'Unknown'
    if (!byDay[day]) byDay[day] = { date: day, total: 0, approved: 0, flagged: 0 }
    byDay[day].total++
    if (['AUTO_APPROVED', 'APPROVED'].includes(t.status)) byDay[day].approved++
    if (t.risk_score > 0.5) byDay[day].flagged++
  })
  return Object.values(byDay).sort((a, b) => a.date.localeCompare(b.date)).slice(-14)
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-background border rounded-lg shadow-lg px-3 py-2 text-xs">
      <p className="font-semibold mb-1">{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color }}>{p.name}: {p.value}</p>
      ))}
    </div>
  )
}

export function DashboardCharts({ triplets = [], fraudAlerts = [], stats = null }) {
  const confidenceBuckets = useMemo(() => buildConfidenceBuckets(triplets), [triplets])
  const statusData        = useMemo(() => buildStatusData(triplets),         [triplets])
  const fraudData         = useMemo(() => buildFraudData(fraudAlerts),       [fraudAlerts])
  const trendData         = useMemo(() => buildTrends(triplets),             [triplets])

  const noTriplets = triplets.length === 0
  const noFraud    = fraudAlerts.length === 0

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

      {/* Confidence Histogram */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <BarChart2 className="h-4 w-4 text-blue-500" />
            Confidence Score Distribution
          </CardTitle>
        </CardHeader>
        <CardContent>
          {noTriplets ? (
            <EmptyChart message="No triplets to display" />
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={confidenceBuckets} margin={{ top: 4, right: 8, bottom: 4, left: -20 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="label" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} allowDecimals={false} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="count" name="Triplets" radius={[4, 4, 0, 0]}>
                  {confidenceBuckets.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {/* Fraud Breakdown */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <PieIcon className="h-4 w-4 text-red-500" />
            Fraud Alert Breakdown
          </CardTitle>
        </CardHeader>
        <CardContent>
          {noFraud ? (
            <EmptyChart message="No fraud alerts" icon="🛡️" />
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={fraudData}
                  dataKey="value"
                  nameKey="type"
                  cx="50%"
                  cy="50%"
                  outerRadius={70}
                  innerRadius={35}
                  paddingAngle={3}
                  label={({ type, percent }) => `${type} ${(percent * 100).toFixed(0)}%`}
                  labelLine={false}
                >
                  {fraudData.map((entry, i) => (
                    <Cell key={i} fill={FRAUD_COLORS[entry.type] || COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(val, name) => [val, name]} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {/* Status Distribution */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-green-500" />
            Triplet Status Breakdown
          </CardTitle>
        </CardHeader>
        <CardContent>
          {noTriplets ? (
            <EmptyChart message="No triplets to display" />
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={statusData} layout="vertical" margin={{ top: 4, right: 16, bottom: 4, left: 60 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 10 }} allowDecimals={false} />
                <YAxis dataKey="status" type="category" tick={{ fontSize: 9 }} width={75} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="count" name="Count" radius={[0, 4, 4, 0]}>
                  {statusData.map((entry, i) => (
                    <Cell key={i} fill={STATUS_COLORS[entry.status] || COLORS[i % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {/* Trends */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <Activity className="h-4 w-4 text-purple-500" />
            Processing Trends (last 14 days)
          </CardTitle>
        </CardHeader>
        <CardContent>
          {trendData.length === 0 ? (
            <EmptyChart message="Not enough data for trends" />
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={trendData} margin={{ top: 4, right: 8, bottom: 4, left: -20 }}>
                <defs>
                  <linearGradient id="gTotal"    x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#3b82f6" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}   />
                  </linearGradient>
                  <linearGradient id="gApproved" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#22c55e" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#22c55e" stopOpacity={0}   />
                  </linearGradient>
                  <linearGradient id="gFlagged"  x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#ef4444" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0}   />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="date" tick={{ fontSize: 9 }} />
                <YAxis tick={{ fontSize: 10 }} allowDecimals={false} />
                <Tooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ fontSize: 10 }} />
                <Area type="monotone" dataKey="total"    name="Total"    stroke="#3b82f6" fill="url(#gTotal)"    strokeWidth={2} dot={false} />
                <Area type="monotone" dataKey="approved" name="Approved" stroke="#22c55e" fill="url(#gApproved)" strokeWidth={2} dot={false} />
                <Area type="monotone" dataKey="flagged"  name="Flagged"  stroke="#ef4444" fill="url(#gFlagged)"  strokeWidth={2} dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

    </div>
  )
}

function EmptyChart({ message, icon = '📊' }) {
  return (
    <div className="h-[200px] flex flex-col items-center justify-center text-muted-foreground text-sm gap-2">
      <span className="text-3xl">{icon}</span>
      <p>{message}</p>
    </div>
  )
}
