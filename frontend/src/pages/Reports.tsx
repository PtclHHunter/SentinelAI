import { useEffect, useState } from 'react'
import { FileBarChart, Download, Trash2, FileText, FileJson, Table } from 'lucide-react'
import { reportsAPI } from '../services/api'
import { useToast } from '../App'
import type { Report, PaginatedResponse } from '../types'

export default function ReportsPage() {
  const { toast } = useToast()
  const [reports, setReports] = useState<PaginatedResponse<Report> | null>(null)
  const [loading, setLoading] = useState(true)
  const [showGenerate, setShowGenerate] = useState(false)
  const [genForm, setGenForm] = useState({ investigation_id: '', alert_id: '', format: 'pdf', title: '' })

  const loadReports = () => {
    setLoading(true)
    reportsAPI.list({ page_size: 50 })
      .then(r => { setReports(r); setLoading(false) })
      .catch(e => { console.error(e); setLoading(false) })
  }

  useEffect(() => { loadReports() }, [])

  const handleGenerate = async () => {
    if (!genForm.investigation_id && !genForm.alert_id) {
      toast('Enter an investigation or alert ID', 'error')
      return
    }
    try {
      const data: any = { format: genForm.format }
      if (genForm.investigation_id) data.investigation_id = parseInt(genForm.investigation_id)
      if (genForm.alert_id) data.alert_id = parseInt(genForm.alert_id)
      if (genForm.title) data.title = genForm.title
      await reportsAPI.generate(data)
      toast('Report generated', 'success')
      setShowGenerate(false)
      setGenForm({ investigation_id: '', alert_id: '', format: 'pdf', title: '' })
      loadReports()
    } catch (e: any) { toast(e.message, 'error') }
  }

  const handleDelete = async (id: number) => {
    try {
      await reportsAPI.remove(id)
      toast('Report deleted', 'success')
      loadReports()
    } catch (e: any) { toast(e.message, 'error') }
  }

  const formatIcon = (f: string) => {
    switch (f) {
      case 'pdf': return <FileText className="w-4 h-4 text-sentinel-critical" />
      case 'json': return <FileJson className="w-4 h-4 text-sentinel-high" />
      case 'csv': return <Table className="w-4 h-4 text-sentinel-low" />
      default: return <FileBarChart className="w-4 h-4" />
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold flex items-center gap-2"><FileBarChart className="w-6 h-6 text-sentinel-cyan" /> Reports</h2>
        <button onClick={() => setShowGenerate(true)} className="px-4 py-2 bg-sentinel-cyan text-sentinel-bg rounded-lg text-sm font-medium hover:bg-sentinel-cyan/90 flex items-center gap-2">
          <FileBarChart className="w-4 h-4" /> Generate Report
        </button>
      </div>

      {showGenerate && (
        <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-sentinel-text-secondary mb-3">Generate Report</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <input value={genForm.investigation_id} onChange={e => setGenForm(f => ({ ...f, investigation_id: e.target.value }))}
              className="bg-sentinel-bg border border-sentinel-border rounded-lg px-3 py-2 text-sm" placeholder="Investigation ID (optional)" type="number" />
            <input value={genForm.alert_id} onChange={e => setGenForm(f => ({ ...f, alert_id: e.target.value }))}
              className="bg-sentinel-bg border border-sentinel-border rounded-lg px-3 py-2 text-sm" placeholder="Alert ID (optional)" type="number" />
            <select value={genForm.format} onChange={e => setGenForm(f => ({ ...f, format: e.target.value }))}
              className="bg-sentinel-bg border border-sentinel-border rounded-lg px-3 py-2 text-sm">
              <option value="pdf">PDF</option><option value="json">JSON</option><option value="csv">CSV</option>
            </select>
            <input value={genForm.title} onChange={e => setGenForm(f => ({ ...f, title: e.target.value }))}
              className="bg-sentinel-bg border border-sentinel-border rounded-lg px-3 py-2 text-sm" placeholder="Report title (optional)" />
          </div>
          <div className="flex gap-3 mt-3">
            <button onClick={handleGenerate} className="px-6 py-2 bg-sentinel-cyan text-sentinel-bg rounded-lg text-sm font-medium hover:bg-sentinel-cyan/90">Generate</button>
            <button onClick={() => setShowGenerate(false)} className="px-4 py-2 text-sentinel-text-secondary hover:text-sentinel-text text-sm">Cancel</button>
          </div>
        </div>
      )}

      <div className="bg-sentinel-card border border-sentinel-border rounded-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="text-left text-sentinel-text-secondary border-b border-sentinel-border">
              <th className="px-5 py-3 font-medium">Format</th>
              <th className="px-5 py-3 font-medium">Title</th>
              <th className="px-5 py-3 font-medium">Type</th>
              <th className="px-5 py-3 font-medium">Size</th>
              <th className="px-5 py-3 font-medium">Generated</th>
              <th className="px-5 py-3 font-medium">Actions</th>
            </tr></thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={6} className="px-5 py-8 text-center text-sentinel-text-secondary">Loading...</td></tr>
              ) : !reports?.items.length ? (
                <tr><td colSpan={6} className="px-5 py-12 text-center text-sentinel-text-secondary">No reports generated yet</td></tr>
              ) : reports.items.map(r => (
                <tr key={r.id} className="border-b border-sentinel-border hover:bg-sentinel-border/30">
                  <td className="px-5 py-3 flex items-center gap-2">{formatIcon(r.format)}<span className="uppercase text-xs font-medium">{r.format}</span></td>
                  <td className="px-5 py-3">{r.title}</td>
                  <td className="px-5 py-3 text-xs text-sentinel-text-secondary">{r.investigation_id ? `Investigation #${r.investigation_id}` : r.alert_id ? `Alert #${r.alert_id}` : '-'}</td>
                  <td className="px-5 py-3 text-xs text-sentinel-text-secondary">{r.file_size ? `${(r.file_size / 1024).toFixed(1)} KB` : '-'}</td>
                  <td className="px-5 py-3 text-xs text-sentinel-text-secondary">{new Date(r.created_at).toLocaleString()}</td>
                  <td className="px-5 py-3 flex gap-2">
                    <a href={reportsAPI.downloadUrl(r.id)} download className="p-1.5 bg-sentinel-cyan/10 text-sentinel-cyan rounded hover:bg-sentinel-cyan/20 transition-colors">
                      <Download className="w-4 h-4" />
                    </a>
                    <button onClick={() => handleDelete(r.id)} className="p-1.5 bg-sentinel-critical/10 text-sentinel-critical rounded hover:bg-sentinel-critical/20 transition-colors">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}