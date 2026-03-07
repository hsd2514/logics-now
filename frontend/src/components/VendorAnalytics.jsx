import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useToast } from '@/components/Toaster';
import { AlertTriangle, TrendingUp, Users, DollarSign, Activity, RefreshCw } from 'lucide-react';
import { BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { VendorRouteGlobe } from './VendorRouteGlobe';

export function VendorAnalytics() {
  const [analytics, setAnalytics] = useState(null);
  const [profiles, setProfiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedVendor, setSelectedVendor] = useState(null);
  const [sortBy, setSortBy] = useState('risk_score');
  const { addToast } = useToast();

  useEffect(() => {
    loadData();
  }, [sortBy]);

  const loadData = async () => {
    setLoading(true);
    try {
      // Load analytics
      const analyticsRes = await fetch('/api/vendors/analytics');
      const analyticsData = await analyticsRes.json();
      setAnalytics(analyticsData);

      // Load vendor profiles
      const profilesRes = await fetch(`/api/vendors/profiles?limit=50&sort_by=${sortBy}`);
      const profilesData = await profilesRes.json();
      setProfiles(profilesData.profiles);
    } catch (error) {
      addToast('Failed to load vendor analytics', 'error');
    } finally {
      setLoading(false);
    }
  };

  const refreshProfiles = async () => {
    try {
      const res = await fetch('/api/vendors/refresh', { method: 'POST' });
      const data = await res.json();
      addToast(data.message, 'success');
      loadData();
    } catch (error) {
      addToast('Failed to refresh profiles', 'error');
    }
  };

  const loadVendorDetails = async (vendorName) => {
    try {
      const res = await fetch(`/api/vendors/${encodeURIComponent(vendorName)}`);
      const data = await res.json();
      setSelectedVendor(data);
    } catch (error) {
      addToast('Failed to load vendor details', 'error');
    }
  };

  const getRiskBadge = (riskScore) => {
    if (riskScore >= 75) return <Badge variant="destructive">Critical</Badge>;
    if (riskScore >= 50) return <Badge className="bg-orange-600 dark:bg-orange-500 text-white">High</Badge>;
    if (riskScore >= 25) return <Badge className="bg-yellow-500 text-black">Medium</Badge>;
    return <Badge className="bg-green-600 dark:bg-green-500 text-white">Low</Badge>;
  };

  const getFlags = (profile) => {
    const flags = [];
    const total = Number(profile.total_invoices || 0);
    const avg = Number(profile.avg_amount || 0);
    const std = Number(profile.std_deviation || 0);
    const freq = Number(profile.avg_frequency || 0);
    const fraudRate = Number(profile.historical_fraud_rate || 0);
    const cv = avg > 0 ? std / avg : 0;

    if (fraudRate > 0) flags.push({ label: 'Fraud history', tone: 'destructive' });
    if (total > 0 && total < 5) flags.push({ label: 'New vendor', tone: 'warning' });
    if (total > 0 && freq < 1) flags.push({ label: 'Low frequency', tone: 'warning' });
    if (cv > 0.3) flags.push({ label: 'High variance', tone: 'warning' });
    if (Number(profile.risk_score || 0) >= 50) flags.push({ label: 'High risk', tone: 'destructive' });

    return flags.slice(0, 3);
  };

  if (loading) {
    return <div className="p-8 text-center">Loading vendor analytics...</div>;
  }

  if (!analytics) {
    return <div className="p-8 text-center">No vendor data available</div>;
  }

  // Prepare chart data
  const riskDistributionData = [
    { name: 'Low', value: analytics.risk_distribution.low, color: '#22c55e' },
    { name: 'Medium', value: analytics.risk_distribution.medium, color: '#eab308' },
    { name: 'High', value: analytics.risk_distribution.high, color: '#f97316' },
    { name: 'Critical', value: analytics.risk_distribution.critical, color: '#ef4444' }
  ];

  const topRiskyVendors = profiles
    .filter(p => p.risk_score > 50)
    .slice(0, 10)
    .map(p => ({
      name: p.vendor_name.length > 20 ? p.vendor_name.substring(0, 20) + '...' : p.vendor_name,
      risk: p.risk_score
    }));

  return (
    <div className="space-y-6 p-4 sm:p-6 min-w-0">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:justify-between sm:items-center">
        <h2 className="text-2xl sm:text-3xl font-bold">Vendor Analytics</h2>
        <Button onClick={refreshProfiles} variant="outline" size="sm">
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Vendors</p>
                <h3 className="text-3xl font-bold">{analytics.total_vendors}</h3>
              </div>
              <Users className="w-12 h-12 text-blue-500 opacity-50" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">High Risk Vendors</p>
                <h3 className="text-3xl font-bold text-red-500">{analytics.high_risk_count}</h3>
              </div>
              <AlertTriangle className="w-12 h-12 text-red-500 opacity-50" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Avg Risk Score</p>
                <h3 className="text-3xl font-bold">{analytics.avg_risk_score.toFixed(1)}</h3>
              </div>
              <Activity className="w-12 h-12 text-yellow-500 opacity-50" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Avg Transaction</p>
                <h3 className="text-3xl font-bold">₹{(analytics.avg_transaction_value / 1000).toFixed(0)}K</h3>
              </div>
              <DollarSign className="w-12 h-12 text-green-500 opacity-50" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 3D Route Visualization */}
      <div>
        <h3 className="text-2xl font-semibold mb-4">Shipping Routes Visualization</h3>
        <VendorRouteGlobe vendors={profiles} height={420} />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Risk Distribution Pie Chart */}
        <Card className="min-w-0">
          <CardHeader>
            <CardTitle>Risk Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={riskDistributionData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  label={(entry) => `${entry.name}: ${entry.value}`}
                >
                  {riskDistributionData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Top Risky Vendors Bar Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Top Risky Vendors</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={topRiskyVendors} layout="vertical" margin={{ left: 8, right: 8 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" domain={[0, 100]} />
                <YAxis dataKey="name" type="category" width={90} />
                <Tooltip />
                <Bar dataKey="risk" fill="#ef4444" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Vendor Profiles Table */}
      <Card className="min-w-0">
        <CardHeader>
          <div className="flex flex-col gap-2 sm:flex-row sm:justify-between sm:items-center">
            <CardTitle>Vendor Profiles</CardTitle>
            <div className="flex gap-2">
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="px-3 py-1 border rounded-md text-sm w-full sm:w-auto"
              >
                <option value="risk_score">Sort by Risk</option>
                <option value="total_invoices">Sort by Volume</option>
                <option value="avg_amount">Sort by Amount</option>
                <option value="vendor_name">Sort by Name</option>
              </select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px]">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-3 px-4">Vendor Name</th>
                  <th className="text-left py-3 px-4">Risk Score</th>
                  <th className="text-right py-3 px-4">Transactions</th>
                  <th className="text-right py-3 px-4">Avg Amount</th>
                  <th className="text-right py-3 px-4">Fraud Rate</th>
                  <th className="text-left py-3 px-4">Flags</th>
                  <th className="text-center py-3 px-4">Action</th>
                </tr>
              </thead>
              <tbody>
                {profiles.map((profile) => (
                  <tr key={profile.vendor_name} className="border-b hover:bg-muted/50">
                    <td className="py-3 px-4 font-medium max-w-[240px] truncate" title={profile.vendor_name}>{profile.vendor_name}</td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        {getRiskBadge(profile.risk_score)}
                        <span className="text-sm text-muted-foreground">
                          {profile.risk_score.toFixed(1)}
                        </span>
                      </div>
                    </td>
                    <td className="text-right py-3 px-4">{profile.total_invoices}</td>
                    <td className="text-right py-3 px-4">
                      ₹{(profile.avg_amount / 1000).toFixed(1)}K
                    </td>
                    <td className="text-right py-3 px-4">
                      {(profile.historical_fraud_rate * 100).toFixed(1)}%
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex flex-wrap gap-1">
                        {getFlags(profile).length === 0 ? (
                          <Badge variant="outline">Normal</Badge>
                        ) : (
                          getFlags(profile).map((flag) => (
                            <Badge
                              key={`${profile.vendor_name}-${flag.label}`}
                              variant={flag.tone === 'destructive' ? 'destructive' : 'secondary'}
                            >
                              {flag.label}
                            </Badge>
                          ))
                        )}
                      </div>
                    </td>
                    <td className="text-center py-3 px-4">
                      <Button
                        onClick={() => loadVendorDetails(profile.vendor_name)}
                        size="sm"
                        variant="outline"
                      >
                        Details
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Vendor Details Modal */}
      {selectedVendor && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <Card className="max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <CardHeader>
              <div className="flex justify-between items-start">
                <div>
                  <CardTitle className="text-2xl">{selectedVendor.profile.vendor_name}</CardTitle>
                  <div className="flex gap-2 mt-2">
                    {getRiskBadge(selectedVendor.profile.risk_score)}
                    <Badge variant="outline">
                      {selectedVendor.profile.total_invoices} Transactions
                    </Badge>
                  </div>
                </div>
                <Button onClick={() => setSelectedVendor(null)} variant="ghost" size="sm">
                  ✕
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {/* Profile Stats */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Avg Amount</p>
                    <p className="text-xl font-bold">₹{(selectedVendor.profile.avg_amount / 1000).toFixed(1)}K</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Std Dev</p>
                    <p className="text-xl font-bold">₹{(selectedVendor.profile.std_deviation / 1000).toFixed(1)}K</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Frequency</p>
                    <p className="text-xl font-bold">{selectedVendor.profile.avg_frequency.toFixed(1)}/mo</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Fraud Rate</p>
                    <p className="text-xl font-bold text-red-500">
                      {(selectedVendor.profile.historical_fraud_rate * 100).toFixed(1)}%
                    </p>
                  </div>
                </div>

                {/* Route Patterns */}
                {selectedVendor.profile.route_patterns?.length > 0 && (
                  <div>
                    <h4 className="font-semibold mb-2">Common Routes</h4>
                    <div className="flex flex-wrap gap-2">
                      {selectedVendor.profile.route_patterns.map((route, idx) => (
                        <Badge key={idx} variant="secondary">
                          {route.route} ({route.count})
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Recent Transactions */}
                <div>
                  <h4 className="font-semibold mb-2">Recent Transactions</h4>
                  <div className="border rounded-lg overflow-hidden">
                    <table className="w-full text-sm">
                      <thead className="bg-muted">
                        <tr>
                          <th className="text-left p-2">Shipment ID</th>
                          <th className="text-right p-2">Amount</th>
                          <th className="text-right p-2">Date</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selectedVendor.recent_transactions.slice(0, 5).map((txn) => (
                          <tr key={txn.id} className="border-t">
                            <td className="p-2">{txn.shipment_id || 'N/A'}</td>
                            <td className="text-right p-2">₹{(txn.amount / 1000).toFixed(1)}K</td>
                            <td className="text-right p-2">
                              {txn.date ? new Date(txn.date).toLocaleDateString() : 'N/A'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Fraud Alerts */}
                {selectedVendor.fraud_alerts?.length > 0 && (
                  <div>
                    <h4 className="font-semibold mb-2 text-red-500">Fraud Alerts ({selectedVendor.fraud_alerts.length})</h4>
                    <div className="space-y-2">
                      {selectedVendor.fraud_alerts.slice(0, 3).map((alert) => (
                        <div key={alert.id} className="border border-red-200 dark:border-red-800 rounded-lg p-3 bg-red-100/50 dark:bg-red-950/20">
                          <div className="flex justify-between items-start">
                            <div>
                              <p className="font-medium text-sm">{alert.alert_type}</p>
                              <p className="text-xs text-muted-foreground">
                                {new Date(alert.detected_at).toLocaleString()}
                              </p>
                            </div>
                            <Badge variant="destructive">
                              Risk: {alert.risk_score.toFixed(0)}
                            </Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
