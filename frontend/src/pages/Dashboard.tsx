import { useEffect, useState } from 'react'
import { AlertTriangle, Shield, Eye, FolderOpen, TrendingUp, Activity, ChevronRight } from 'lucide-react'
import { Chart as ChartJS, ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement, PointElement, LineElement } from 'chart.js'
import { Doughnut, Bar, Line } from 'react-chartjs-2'
import { dashboardAPI } from '../services/api'
import type { DashboardStats, Alert, ThreatTrendPoint, SeverityDistribution } from '../types'

ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement, PointElement, LineElement)

const SEVERITY_COLORS = { critical: '#f85149', high: '#d29922', medium: '#a371f7', low: '#3fb950' }

function StatCard({ icon: Icon, label, value, color }: { icon: typeof Shield; label: string; value: number | string; color: string }) {
  return (
    <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-5 flex items-center gap-4">
      <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${color}`}>
        <Icon className="w-6 h-6" />
      </div>
      <div>
        <div className="text-2xl font-bold">{value}</div>
        <div className="text-sm text-sentinel-text-secondary">{label}</div>
      </div>
    </div>
  )
}

function SeverityBadge({ severity }: { severity: string }) {
  const colors: Record<string, string> = {
    critical: 'bg-sentinel-critical/20 text-sentinel-critical',
    high: 'bg-sentinel-high/20 text-sentinel-high',
    medium: 'bg-sentinel-medium/20 text-sentinel-medium',
    low: 'bg-sentinel-low/20 text-sentinel-low',
  }
  const pulseClass = severity === 'critical' ? 'animate-pulse-critical' : ''
  return (
    <span className={`px-2 py-1 rounded text-xs font-medium ${colors[severity] || 'bg-gray-500/20 text-gray-400'} ${pulseClass}`}>
      {severity.toUpperCase()}
    </span>
  )
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [trends, setTrends] = useState<ThreatTrendPoint[]>([])
  const [severityDist, setSeverityDist] = useState<SeverityDistribution[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const [s, a, t, sd] = await Promise.all([
          dashboardAPI.getStats(),
          dashboardAPI.getRecentAlerts({ page_size: 8 }),
          dashboardAPI.getTrends(24),
          dashboardAPI.getSeverityDistribution(),
        ])
        setStats(s)
        setAlerts(a.items)
        setTrends(t)
        setSeverityDist(sd)
      } catch (e) { console.error(e) }
      setLoading(false)
    }
    load()
  }, [])

  if (loading) return <div className="flex items-center justify-center h-64 text-sentinel-text-secondary">Loading dashboard...</div>
  if (!stats) return <div className="text-sentinel-critical">Failed to load dashboard</div>

  // Chart data
  const severityDoughnut = {
    labels: severityDist.map(s => s.severity),
    datasets: [{
      data: severityDist.map(s => s.count),
      backgroundColor: severityDist.map(s => SEVERITY_COLORS[s.severity as keyof typeof SEVERITY_COLORS] || '#666'),
      borderWidth: 0,
    }],
  }

  const trendData = {
    labels: [...new Set(trends.map(t => new Date(t.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })))].slice(-12),
    datasets: ['critical', 'high', 'medium', 'low'].map(sev => ({
      label: sev,
      data: (() => {
        const times = [...new Set(trends.map(t => new Date(t.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })))]
        return times.slice(-12).map(time => trends.filter(t =>
          t.severity === sev && new Date(t.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) === time
        ).reduce((sum, t) => sum + t.count, 0))
      })(),
      borderColor: SEVERITY_COLORS[sev as keyof typeof SEVERITY_COLORS],
      backgroundColor: SEVERITY_COLORS[sev as keyof typeof SEVERITY_COLORS] + '20',
      tension: 0.4,
      fill: true,
    })),
  }

  const barData = {
    labels: severityDist.map(s => s.severity.toUpperCase()),
    datasets: [{
      data: severityDist.map(s => s.count),
      backgroundColor: severityDist.map(s => SEVERITY_COLORS[s.severity as keyof typeof SEVERITY_COLORS] + '80'),
      borderColor: severityDist.map(s => SEVERITY_COLORS[s.severity as keyof typeof SEVERITY_COLORS]),
      borderWidth: 1,
    }],
  }

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { labels: { color: '#8b949e', font: { size: 11 } } } },
    scales: {
      x: { ticks: { color: '#8b949e', font: { size: 10 } }, grid: { color: '#30363d' } },
      y: { ticks: { color: '#8b949e', font: { size: 10 } }, grid: { color: '#30363d' }, beginAtZero: true },
    },
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold flex items-center gap-2"><Shield className="w-6 h-6 text-sentinel-cyan" /> Security Dashboard</h2>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={Activity} label="Total Events" value={stats.total_events} color="bg-sentinel-cyan/10 text-sentinel-cyan" />
        <StatCard icon={AlertTriangle} label="Total Alerts" value={stats.total_alerts} color="bg-sentinel-purple/10 text-sentinel-purple" />
        <StatCard icon={AlertTriangle} label="Critical Alerts" value={stats.critical_alerts} color="bg-sentinel-critical/10 text-sentinel-critical" />
        <StatCard icon={FolderOpen} label="Investigations" value={stats.total_investigations} color="bg-sentinel-high/10 text-sentinel-high" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-sentinel-card border border-sentinel-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-sentinel-text-secondary mb-4 flex items-center gap-2"><TrendingUp className="w-4 h-4" /> Threat Trends (24h)</h3>
          <div className="h-64"><Line data={trendData} options={{ ...chartOptions, plugins: { ...chartOptions.plugins, legend: { ...chartOptions.plugins.legend, position: 'bottom' as const } } }} /></div>
        </div>
        <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-sentinel-text-secondary mb-4">Severity Distribution</h3>
          <div className="h-48 flex justify-center"><Doughnut data={severityDoughnut} options={{ responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' as const, labels: { color: '#8b949e', font: { size: 10 } } } } }} /></div>
          <div className="mt-4 h-32"><Bar data={barData} options={{ ...chartOptions, plugins: { legend: { display: false } } }} /></div>
        </div>
      </div>

      <div className="bg-sentinel-card border border-sentinel-border rounded-xl">
        <div className="flex items-center justify-between p-5 border-b border-sentinel-border">
          <h3 className="text-sm font-semibold text-sentinel-text-secondary flex items-center gap-2"><Eye className="w-4 h-4" /> Recent Alerts</h3>
          <span className="text-xs text-sentinel-text-secondary">{stats.recent_alerts_count} in 24h</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-sentinel-text-secondary border-b border-sentinel-border">
                <th className="px-5 py-3 font-medium">Rule</th>
                <th className="px-5 py-3 font-medium">Title</th>
                <th className="px-5 py-3 font-medium">Severity</th>
                <th className="px-5 py-3 font-medium">Confidence</th>
                <th className="px-5 py-3 font-medium">Source</th>
                <th className="px-5 py-3 font-medium">Time</th>
                <th className="px-5 py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {alerts.length === 0 ? (
                <tr><td colSpan={7} className="px-5 py-12 text-center text-sentinel-text-secondary">No alerts yet. Upload a log file to get started.</td></tr>
              ) : alerts.map(a => (
                <tr key={a.id} className="border-b border-sentinel-border hover:bg-sentinel-border/30 transition-colors">
                  <td className="px-5 py-3 font-mono text-xs text-sentinel-cyan">{a.rule_id}</td>
                  <td className="px-5 py-3 max-w-xs truncate">{a.title}</td>
                  <td className="px-5 py-3"><SeverityBadge severity={a.severity} /></td>
                  <td className="px-5 py-3">{a.confidence}%</td>
                  <td className="px-5 py-3 text-xs text-sentinel-text-secondary truncate max-w-[120px]">{a.source_file}</td>
                  <td className="px-5 py-3 text-xs text-sentinel-text-secondary">{new Date(a.timestamp).toLocaleString()}</td>
                  <td className="px-5 py-3"><span className={`text-xs px-2 py-1 rounded ${a.status === 'new' ? 'bg-sentinel-cyan/10 text-sentinel-cyan' : a.status === 'investigating' ? 'bg-sentinel-high/10 text-sentinel-high' : 'bg-sentinel-low/10 text-sentinel-low'}`}>{a.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}