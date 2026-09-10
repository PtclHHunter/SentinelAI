import { useEffect, useState } from 'react'
import { Search, Plus, Trash2, Database, AlertTriangle } from 'lucide-react'
import { iocAPI } from '../services/api'
import { useToast } from '../App'
import type { IOCRecord, IOCScanResponse, IOCStats, PaginatedResponse } from '../types'

export default function IOCScannerPage() {
  const { toast } = useToast()
  const [scanInput, setScanInput] = useState('')
  const [scanResult, setScanResult] = useState<IOCScanResponse | null>(null)
  const [scanning, setScanning] = useState(false)
  const [dbIOCs, setDbIOCs] = useState<PaginatedResponse<IOCRecord> | null>(null)
  const [stats, setStats] = useState<IOCStats | null>(null)
  const [activeTab, setActiveTab] = useState<'scan' | 'database'>('scan')
  const [addForm, setAddForm] = useState({ ioc_type: 'ipv4' as const, value: '', description: '' })
  const [searchTerm, setSearchTerm] = useState('')
  const [dbPage, setDbPage] = useState(1)

  const loadDB = (page = 1, search = '') => {
    iocAPI.list({ page, page_size: 10, search }).then(setDbIOCs).catch(console.error)
    setDbPage(page)
  }

  useEffect(() => {
    loadDB()
    iocAPI.getStats().then(setStats).catch(console.error)
  }, [])

  const handleScan = async () => {
    if (!scanInput.trim()) return
    setScanning(true)
    try {
      const res = await iocAPI.scan(scanInput)
      setScanResult(res)
      toast(`Found ${res.matches.length} IOC matches`, res.matches.length > 0 ? 'error' : 'info')
    } catch (e: any) { toast(e.message, 'error') }
    setScanning(false)
  }

  const handleAdd = async () => {
    if (!addForm.value.trim()) return
    try {
      await iocAPI.create(addForm)
      toast('IOC added successfully', 'success')
      setAddForm({ ioc_type: 'ipv4', value: '', description: '' })
      loadDB(dbPage, searchTerm)
      iocAPI.getStats().then(setStats).catch(console.error)
    } catch (e: any) { toast(e.message, 'error') }
  }

  const handleDelete = async (id: number) => {
    try {
      await iocAPI.remove(id)
      toast('IOC deleted', 'success')
      loadDB(dbPage, searchTerm)
      iocAPI.getStats().then(setStats).catch(console.error)
    } catch (e: any) { toast(e.message, 'error') }
  }

  const handleSearch = () => { loadDB(1, searchTerm) }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold flex items-center gap-2"><Search className="w-6 h-6 text-sentinel-cyan" /> IOC Scanner</h2>

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="bg-sentinel-card border border-sentinel-border rounded-lg p-4 text-center">
            <div className="text-xl font-bold text-sentinel-cyan">{stats.total}</div>
            <div className="text-xs text-sentinel-text-secondary">Total IOCs</div>
          </div>
          <div className="bg-sentinel-card border border-sentinel-border rounded-lg p-4 text-center">
            <div className="text-xl font-bold text-sentinel-low">{stats.active}</div>
            <div className="text-xs text-sentinel-text-secondary">Active</div>
          </div>
          {Object.entries(stats.by_type).filter(([, v]: [string, number]) => v > 0).map(([k, v]: [string, number]) => (
            <div key={k} className="bg-sentinel-card border border-sentinel-border rounded-lg p-4 text-center">
              <div className="text-xl font-bold text-sentinel-purple">{v}</div>
              <div className="text-xs text-sentinel-text-secondary uppercase">{k}</div>
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-2 border-b border-sentinel-border">
        {(['scan', 'database'] as const).map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${activeTab === tab ? 'border-sentinel-cyan text-sentinel-cyan' : 'border-transparent text-sentinel-text-secondary hover:text-sentinel-text'}`}>
            {tab === 'scan' ? 'Scan Text' : 'IOC Database'}
          </button>
        ))}
      </div>

      {activeTab === 'scan' && (
        <div className="space-y-4">
          <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-5">
            <label className="text-sm text-sentinel-text-secondary mb-2 block">Paste text, logs, or content to scan for IOCs</label>
            <textarea value={scanInput} onChange={e => setScanInput(e.target.value)}
              className="w-full h-40 bg-sentinel-bg border border-sentinel-border rounded-lg p-3 text-sm text-sentinel-text placeholder-sentinel-text-secondary resize-none focus:outline-none focus:border-sentinel-cyan"
              placeholder="Paste suspicious text, log entries, or content here..." />
            <button onClick={handleScan} disabled={scanning || !scanInput.trim()}
              className="mt-3 px-6 py-2 bg-sentinel-cyan text-sentinel-bg rounded-lg text-sm font-medium hover:bg-sentinel-cyan/90 transition-colors disabled:opacity-50 flex items-center gap-2">
              <Search className="w-4 h-4" /> {scanning ? 'Scanning...' : 'Scan for IOCs'}
            </button>
          </div>

          {scanResult && (
            <div className="space-y-4">
              <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-5">
                <h3 className="text-sm font-semibold text-sentinel-text-secondary mb-3">Extracted IOCs</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {Object.entries(scanResult.extracted_iocs).filter(([, v]: [string, string[]]) => v.length > 0).map(([type, values]: [string, string[]]) => (
                    <div key={type} className="bg-sentinel-bg border border-sentinel-border rounded-lg p-3">
                      <div className="text-xs font-medium text-sentinel-cyan uppercase mb-2">{type} ({values.length})</div>
                      <div className="space-y-1 max-h-24 overflow-y-auto">
                        {values.map((v, i) => (
                          <div key={i} className="text-xs font-mono text-sentinel-text truncate">{v}</div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {scanResult.matches.length > 0 && (
                <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-5">
                  <h3 className="text-sm font-semibold text-sentinel-critical mb-3 flex items-center gap-2"><AlertTriangle className="w-4 h-4" /> IOC Matches ({scanResult.matches.length})</h3>
                  <div className="space-y-2">
                    {scanResult.matches.map((m, i) => (
                      <div key={i} className="bg-sentinel-bg border border-sentinel-critical/30 rounded-lg p-3">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs px-2 py-0.5 rounded bg-sentinel-critical/20 text-sentinel-critical font-medium uppercase">{m.ioc_type}</span>
                          <span className="text-sm font-mono text-sentinel-critical">{m.value}</span>
                        </div>
                        <div className="text-xs text-sentinel-text-secondary">{m.matched_ioc.description}</div>
                        <div className="text-xs text-sentinel-text-secondary mt-1 truncate">Context: {m.context}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="text-xs text-sentinel-text-secondary">Scan time: {scanResult.scan_time_ms.toFixed(1)}ms</div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'database' && (
        <div className="space-y-4">
          <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-5">
            <h3 className="text-sm font-semibold text-sentinel-text-secondary mb-3 flex items-center gap-2"><Plus className="w-4 h-4" /> Add IOC</h3>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
              <select value={addForm.ioc_type} onChange={e => setAddForm(f => ({ ...f, ioc_type: e.target.value as any }))}
                className="bg-sentinel-bg border border-sentinel-border rounded-lg px-3 py-2 text-sm">
                <option value="ipv4">IPv4</option><option value="domain">Domain</option><option value="url">URL</option>
                <option value="md5">MD5</option><option value="sha1">SHA-1</option><option value="sha256">SHA-256</option><option value="sha512">SHA-512</option>
              </select>
              <input value={addForm.value} onChange={e => setAddForm(f => ({ ...f, value: e.target.value }))}
                className="bg-sentinel-bg border border-sentinel-border rounded-lg px-3 py-2 text-sm" placeholder="IOC value" />
              <input value={addForm.description} onChange={e => setAddForm(f => ({ ...f, description: e.target.value }))}
                className="bg-sentinel-bg border border-sentinel-border rounded-lg px-3 py-2 text-sm" placeholder="Description (optional)" />
              <button onClick={handleAdd} className="px-4 py-2 bg-sentinel-cyan text-sentinel-bg rounded-lg text-sm font-medium hover:bg-sentinel-cyan/90 transition-colors">Add</button>
            </div>
          </div>

          <div className="bg-sentinel-card border border-sentinel-border rounded-xl">
            <div className="p-4 border-b border-sentinel-border flex items-center gap-3">
              <Database className="w-4 h-4 text-sentinel-text-secondary" />
              <h3 className="text-sm font-semibold text-sentinel-text-secondary">Local IOC Database</h3>
              <input value={searchTerm} onChange={e => setSearchTerm(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleSearch()}
                className="ml-auto bg-sentinel-bg border border-sentinel-border rounded-lg px-3 py-1.5 text-sm w-48" placeholder="Search IOCs..." />
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="text-left text-sentinel-text-secondary border-b border-sentinel-border">
                  <th className="px-4 py-2 font-medium">Type</th><th className="px-4 py-2 font-medium">Value</th>
                  <th className="px-4 py-2 font-medium">Description</th><th className="px-4 py-2 font-medium">Source</th>
                  <th className="px-4 py-2 font-medium">Created</th><th className="px-4 py-2 font-medium w-12"></th>
                </tr></thead>
                <tbody>
                  {!dbIOCs?.items.length ? (
                    <tr><td colSpan={6} className="px-4 py-8 text-center text-sentinel-text-secondary">No IOCs found</td></tr>
                  ) : dbIOCs.items.map(ioc => (
                    <tr key={ioc.id} className="border-b border-sentinel-border hover:bg-sentinel-border/30">
                      <td className="px-4 py-2"><span className="text-xs px-2 py-0.5 rounded bg-sentinel-purple/20 text-sentinel-purple uppercase">{ioc.ioc_type}</span></td>
                      <td className="px-4 py-2 font-mono text-xs">{ioc.value}</td>
                      <td className="px-4 py-2 text-xs text-sentinel-text-secondary max-w-[200px] truncate">{ioc.description}</td>
                      <td className="px-4 py-2 text-xs text-sentinel-text-secondary">{ioc.source}</td>
                      <td className="px-4 py-2 text-xs text-sentinel-text-secondary">{ioc.created_at ? new Date(ioc.created_at).toLocaleDateString() : '-'}</td>
                      <td className="px-4 py-2">
                        <button onClick={() => handleDelete(ioc.id!)} className="p-1 text-sentinel-text-secondary hover:text-sentinel-critical transition-colors">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {dbIOCs && dbIOCs.total_pages > 1 && (
              <div className="flex items-center justify-between p-4 border-t border-sentinel-border">
                <span className="text-xs text-sentinel-text-secondary">{dbIOCs.total} total IOCs</span>
                <div className="flex gap-1">
                  {Array.from({ length: Math.min(dbIOCs.total_pages, 5) }, (_, i) => i + 1).map(p => (
                    <button key={p} onClick={() => loadDB(p, searchTerm)}
                      className={`px-3 py-1 text-xs rounded ${p === dbPage ? 'bg-sentinel-cyan text-sentinel-bg' : 'bg-sentinel-border text-sentinel-text-secondary hover:bg-sentinel-border/80'}`}>{p}</button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}