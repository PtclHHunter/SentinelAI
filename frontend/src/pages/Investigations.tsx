import { useEffect, useState } from 'react'
import { FolderOpen, Plus, Eye, Clock, MessageSquare, ChevronRight, X } from 'lucide-react'
import { investigationsAPI } from '../services/api'
import { useToast } from '../App'
import type { Investigation, InvestigationStatus, SeverityLevel, Alert } from '../types'

export default function InvestigationsPage() {
  const { toast } = useToast()
  const [investigations, setInvestigations] = useState<Investigation[]>([])
  const [selected, setSelected] = useState<Investigation | null>(null)
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [createForm, setCreateForm] = useState({ title: '', description: '', severity: 'medium' as SeverityLevel })
  const [noteText, setNoteText] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [detailLoading, setDetailLoading] = useState(false)

  const loadList = () => {
    setLoading(true)
    investigationsAPI.list({ status: statusFilter || undefined, page_size: 50 })
      .then(r => { setInvestigations(r.items); setLoading(false) })
      .catch(e => { console.error(e); setLoading(false) })
  }

  useEffect(() => { loadList() }, [statusFilter])

  const loadDetail = async (id: number) => {
    setDetailLoading(true)
    try {
      const inv = await investigationsAPI.get(id)
      setSelected(inv)
    } catch (e: any) { toast(e.message, 'error') }
    setDetailLoading(false)
  }

  const handleCreate = async () => {
    if (!createForm.title.trim()) return
    try {
      const inv = await investigationsAPI.create(createForm)
      toast('Investigation created', 'success')
      setShowCreate(false)
      setCreateForm({ title: '', description: '', severity: 'medium' })
      loadList()
      loadDetail(inv.id)
    } catch (e: any) { toast(e.message, 'error') }
  }

  const handleStatusChange = async (id: number, status: string) => {
    try {
      await investigationsAPI.update(id, { status })
      toast(`Status updated to ${status}`, 'success')
      loadList()
      if (selected?.id === id) loadDetail(id)
    } catch (e: any) { toast(e.message, 'error') }
  }

  const handleAddNote = async () => {
    if (!noteText.trim() || !selected) return
    try {
      await investigationsAPI.addNote(selected.id, noteText)
      toast('Note added', 'success')
      setNoteText('')
      loadDetail(selected.id)
    } catch (e: any) { toast(e.message, 'error') }
  }

  const handleDelete = async (id: number) => {
    try {
      await investigationsAPI.remove(id)
      toast('Investigation deleted', 'success')
      if (selected?.id === id) setSelected(null)
      loadList()
    } catch (e: any) { toast(e.message, 'error') }
  }

  const sevColor = (s: string) => ({
    critical: 'bg-sentinel-critical/20 text-sentinel-critical',
    high: 'bg-sentinel-high/20 text-sentinel-high',
    medium: 'bg-sentinel-medium/20 text-sentinel-medium',
    low: 'bg-sentinel-low/20 text-sentinel-low',
  }[s] || 'bg-gray-500/20 text-gray-400')

  const statusColor = (s: string) => ({
    open: 'bg-sentinel-cyan/10 text-sentinel-cyan',
    in_progress: 'bg-sentinel-high/10 text-sentinel-high',
    closed: 'bg-sentinel-low/10 text-sentinel-low',
  }[s] || 'bg-gray-500/10 text-gray-400')

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold flex items-center gap-2"><FolderOpen className="w-6 h-6 text-sentinel-cyan" /> Investigations</h2>
        <button onClick={() => setShowCreate(true)} className="px-4 py-2 bg-sentinel-cyan text-sentinel-bg rounded-lg text-sm font-medium hover:bg-sentinel-cyan/90 flex items-center gap-2">
          <Plus className="w-4 h-4" /> New Investigation
        </button>
      </div>

      {showCreate && (
        <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-sentinel-text-secondary mb-3">Create Investigation</h3>
          <div className="space-y-3">
            <input value={createForm.title} onChange={e => setCreateForm(f => ({ ...f, title: e.target.value }))}
              className="w-full bg-sentinel-bg border border-sentinel-border rounded-lg px-3 py-2 text-sm" placeholder="Title" />
            <textarea value={createForm.description} onChange={e => setCreateForm(f => ({ ...f, description: e.target.value }))}
              className="w-full h-20 bg-sentinel-bg border border-sentinel-border rounded-lg p-3 text-sm resize-none" placeholder="Description (optional)" />
            <div className="flex gap-3">
              <select value={createForm.severity} onChange={e => setCreateForm(f => ({ ...f, severity: e.target.value as SeverityLevel }))}
                className="bg-sentinel-bg border border-sentinel-border rounded-lg px-3 py-2 text-sm">
                <option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="critical">Critical</option>
              </select>
              <button onClick={handleCreate} className="px-6 py-2 bg-sentinel-cyan text-sentinel-bg rounded-lg text-sm font-medium hover:bg-sentinel-cyan/90">Create</button>
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-sentinel-text-secondary hover:text-sentinel-text text-sm">Cancel</button>
            </div>
          </div>
        </div>
      )}

      <div className="flex gap-2 mb-4">
        {['', 'open', 'in_progress', 'closed'].map(s => (
          <button key={s} onClick={() => setStatusFilter(s)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${statusFilter === s ? 'bg-sentinel-cyan text-sentinel-bg' : 'bg-sentinel-card border border-sentinel-border text-sentinel-text-secondary hover:bg-sentinel-border'}`}>
            {s || 'All'}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-3 max-h-[calc(100vh-200px)] overflow-y-auto">
          {loading ? (
            <div className="text-center text-sentinel-text-secondary py-8">Loading...</div>
          ) : investigations.length === 0 ? (
            <div className="text-center text-sentinel-text-secondary py-8 bg-sentinel-card border border-sentinel-border rounded-xl">No investigations found</div>
          ) : investigations.map(inv => (
            <div key={inv.id} onClick={() => loadDetail(inv.id)}
              className={`bg-sentinel-card border rounded-xl p-4 cursor-pointer transition-colors ${selected?.id === inv.id ? 'border-sentinel-cyan' : 'border-sentinel-border hover:border-sentinel-border/80'}`}>
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-medium text-sm truncate">{inv.title}</h3>
                <span className={`text-xs px-2 py-0.5 rounded ${sevColor(inv.severity)}`}>{inv.severity}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className={`text-xs px-2 py-0.5 rounded ${statusColor(inv.status)}`}>{inv.status.replace('_', ' ')}</span>
                <span className="text-xs text-sentinel-text-secondary">{inv.alert_count} alerts</span>
              </div>
            </div>
          ))}
        </div>

        <div className="lg:col-span-2">
          {detailLoading ? (
            <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-8 text-center text-sentinel-text-secondary">Loading details...</div>
          ) : !selected ? (
            <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-8 text-center text-sentinel-text-secondary">Select an investigation to view details</div>
          ) : (
            <div className="space-y-4">
              <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-5">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="font-bold text-lg">{selected.title}</h3>
                    <p className="text-sm text-sentinel-text-secondary mt-1">{selected.description || 'No description'}</p>
                  </div>
                  <div className="flex gap-2">
                    {selected.status !== 'closed' && (
                      <select value={selected.status} onChange={e => handleStatusChange(selected.id, e.target.value)}
                        className="bg-sentinel-bg border border-sentinel-border rounded-lg px-3 py-1.5 text-sm">
                        <option value="open">Open</option><option value="in_progress">In Progress</option><option value="closed">Closed</option>
                      </select>
                    )}
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div className="text-center"><div className="text-xl font-bold text-sentinel-cyan">{selected.alert_count}</div><div className="text-xs text-sentinel-text-secondary">Alerts</div></div>
                  <div className="text-center"><div className="text-xl font-bold text-sentinel-purple">{selected.evidence_count}</div><div className="text-xs text-sentinel-text-secondary">Evidence</div></div>
                  <div className="text-center"><div className="text-xl font-bold text-sentinel-high">{selected.timeline?.length || 0}</div><div className="text-xs text-sentinel-text-secondary">Timeline</div></div>
                </div>
              </div>

              {selected.timeline && selected.timeline.length > 0 && (
                <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-5">
                  <h4 className="text-sm font-semibold text-sentinel-text-secondary mb-4 flex items-center gap-2"><Clock className="w-4 h-4" /> Timeline</h4>
                  <div className="relative pl-6">
                    <div className="absolute left-2 top-0 bottom-0 w-px bg-sentinel-border"></div>
                    {selected.timeline.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()).map((tl, i) => (
                      <div key={tl.id} className="relative mb-4 last:mb-0">
                        <div className="absolute left-[-18px] top-1 w-3 h-3 rounded-full bg-sentinel-cyan border-2 border-sentinel-card"></div>
                        <div className="text-xs text-sentinel-text-secondary">{new Date(tl.timestamp).toLocaleString()}</div>
                        <div className="text-sm font-medium">{tl.title}</div>
                        {tl.description && <div className="text-xs text-sentinel-text-secondary mt-1">{tl.description}</div>}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-5">
                <h4 className="text-sm font-semibold text-sentinel-text-secondary mb-3 flex items-center gap-2"><MessageSquare className="w-4 h-4" /> Notes</h4>
                <div className="space-y-2 mb-3">
                  {selected.notes?.map(n => (
                    <div key={n.id} className="bg-sentinel-bg border border-sentinel-border rounded-lg p-3">
                      <div className="text-xs text-sentinel-text-secondary mb-1">{n.created_by} - {new Date(n.created_at).toLocaleString()}</div>
                      <div className="text-sm">{n.content}</div>
                    </div>
                  ))}
                </div>
                <div className="flex gap-2">
                  <input value={noteText} onChange={e => setNoteText(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleAddNote()}
                    className="flex-1 bg-sentinel-bg border border-sentinel-border rounded-lg px-3 py-2 text-sm" placeholder="Add a note..." />
                  <button onClick={handleAddNote} className="px-4 py-2 bg-sentinel-cyan text-sentinel-bg rounded-lg text-sm font-medium hover:bg-sentinel-cyan/90">Add</button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}