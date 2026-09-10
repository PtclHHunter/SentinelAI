import { useEffect, useState } from 'react'
import { Upload, FileText, Play, Clock, CheckCircle, AlertCircle, Trash2, RotateCcw } from 'lucide-react'
import { logsAPI } from '../services/api'
import { useToast } from '../App'
import type { SampleLogFile, ParseResult } from '../types'

export default function LogAnalyzerPage() {
  const { toast } = useToast()
  const [samples, setSamples] = useState<SampleLogFile[]>([])
  const [results, setResults] = useState<ParseResult | null>(null)
  const [processing, setProcessing] = useState(false)
  const [jobId, setJobId] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'samples' | 'upload'>('samples')

  useEffect(() => { logsAPI.listSamples().then(setSamples).catch(console.error) }, [])

  const pollResult = (jid: string) => {
    setJobId(jid)
    setProcessing(true)
    const interval = setInterval(async () => {
      try {
        const res = await logsAPI.getParseResult(jid)
        setResults(res)
        setProcessing(false)
        clearInterval(interval)
        setJobId(null)
        toast(`Parsed ${res.parsed_events} events, generated ${res.alerts_generated} alerts`, 'success')
      } catch (e: any) {
        if (e.message?.includes('202')) return // still processing
        clearInterval(interval)
        setProcessing(false)
        toast(`Parse failed: ${e.message}`, 'error')
      }
    }, 1000)
  }

  const handleParseSample = async (filename: string) => {
    try {
      const res = await logsAPI.parseSample(filename)
      pollResult(res.job_id)
    } catch (e: any) { toast(e.message, 'error') }
  }

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      const res = await logsAPI.upload(file)
      pollResult(res.job_id)
    } catch (err: any) { toast(err.message, 'error') }
    e.target.value = ''
  }

  const handleClearResults = () => {
    setResults(null)
    setJobId(null)
    setProcessing(false)
    toast('Results cleared from view', 'info')
  }

  const handleResetAll = async () => {
    if (!window.confirm('This will clear all parsed events and alerts from the database. Continue?')) return
    try {
      const res = await logsAPI.clearAll()
      setResults(null)
      setJobId(null)
      setProcessing(false)
      toast(`Reset complete: ${res.deleted_events} events and ${res.deleted_alerts} alerts removed`, 'success')
    } catch (e: any) { toast(`Reset failed: ${e.message}`, 'error') }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold flex items-center gap-2"><FileText className="w-6 h-6 text-sentinel-cyan" /> Log Analyzer</h2>

      <div className="flex items-center justify-between border-b border-sentinel-border">
        <div className="flex gap-2">
          {(['samples', 'upload'] as const).map(tab => (
            <button key={tab} onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${activeTab === tab ? 'border-sentinel-cyan text-sentinel-cyan' : 'border-transparent text-sentinel-text-secondary hover:text-sentinel-text'}`}>
              {tab === 'samples' ? 'Sample Logs' : 'Upload File'}
            </button>
          ))}
        </div>
        {results && (
          <div className="flex gap-2 pb-1">
            <button onClick={handleClearResults}
              className="px-3 py-1.5 text-xs font-medium text-sentinel-text-secondary hover:text-sentinel-cyan border border-sentinel-border rounded-lg hover:border-sentinel-cyan/50 transition-colors flex items-center gap-1.5">
              <Trash2 className="w-3.5 h-3.5" /> Clear Results
            </button>
            <button onClick={handleResetAll}
              className="px-3 py-1.5 text-xs font-medium text-sentinel-critical hover:text-white border border-sentinel-critical/30 rounded-lg hover:bg-sentinel-critical/20 transition-colors flex items-center gap-1.5">
              <RotateCcw className="w-3.5 h-3.5" /> Reset All
            </button>
          </div>
        )}
      </div>

      {activeTab === 'samples' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {samples.map(s => (
            <div key={s.filename} className="bg-sentinel-card border border-sentinel-border rounded-xl p-5">
              <div className="flex items-start justify-between mb-3">
                <h3 className="font-medium text-sm">{s.filename}</h3>
                <span className="text-xs text-sentinel-text-secondary">{(s.size / 1024).toFixed(1)} KB</span>
              </div>
              <p className="text-xs text-sentinel-text-secondary mb-4 line-clamp-2">{s.description}</p>
              <button onClick={() => handleParseSample(s.filename)} disabled={processing}
                className="w-full px-4 py-2 bg-sentinel-cyan/10 text-sentinel-cyan rounded-lg text-sm font-medium hover:bg-sentinel-cyan/20 transition-colors disabled:opacity-50 flex items-center justify-center gap-2">
                <Play className="w-4 h-4" /> Parse Now
              </button>
            </div>
          ))}
        </div>
      )}

      {activeTab === 'upload' && (
        <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-8 text-center">
          <Upload className="w-12 h-12 mx-auto text-sentinel-text-secondary mb-4" />
          <p className="text-sm text-sentinel-text-secondary mb-4">Upload .log, .txt, .json, or .csv files (max 50MB)</p>
          <label className="inline-flex items-center gap-2 px-6 py-3 bg-sentinel-cyan text-sentinel-bg rounded-lg text-sm font-medium cursor-pointer hover:bg-sentinel-cyan/90 transition-colors">
            <Upload className="w-4 h-4" /> Select File
            <input type="file" className="hidden" accept=".log,.txt,.json,.csv" onChange={handleUpload} />
          </label>
        </div>
      )}

      {processing && (
        <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-6 text-center">
          <div className="animate-spin w-8 h-8 border-2 border-sentinel-cyan border-t-transparent rounded-full mx-auto mb-3"></div>
          <p className="text-sm text-sentinel-text-secondary">Processing log file...</p>
        </div>
      )}

      {results && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {[
              { label: 'Total Lines', value: results.total_lines },
              { label: 'Parsed Events', value: results.parsed_events },
              { label: 'Alerts Generated', value: results.alerts_generated },
              { label: 'Parse Errors', value: results.parse_errors },
              { label: 'File', value: results.filename },
            ].map(s => (
              <div key={s.label} className="bg-sentinel-card border border-sentinel-border rounded-lg p-4 text-center">
                <div className="text-xl font-bold text-sentinel-cyan">{s.value}</div>
                <div className="text-xs text-sentinel-text-secondary mt-1">{s.label}</div>
              </div>
            ))}
          </div>

          {results.alerts.length > 0 && (
            <div className="bg-sentinel-card border border-sentinel-border rounded-xl overflow-hidden">
              <div className="p-4 border-b border-sentinel-border"><h3 className="text-sm font-semibold text-sentinel-text-secondary">Detected Alerts</h3></div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead><tr className="text-left text-sentinel-text-secondary border-b border-sentinel-border">
                    <th className="px-4 py-2 font-medium">Rule</th>
                    <th className="px-4 py-2 font-medium">Title</th>
                    <th className="px-4 py-2 font-medium">Severity</th>
                    <th className="px-4 py-2 font-medium">Confidence</th>
                    <th className="px-4 py-2 font-medium">Source</th>
                    <th className="px-4 py-2 font-medium">Time</th>
                  </tr></thead>
                  <tbody>
                    {results.alerts.map(a => (
                      <tr key={a.id} className="border-b border-sentinel-border hover:bg-sentinel-border/30">
                        <td className="px-4 py-2 font-mono text-xs text-sentinel-cyan">{a.rule_id}</td>
                        <td className="px-4 py-2 max-w-xs truncate">{a.title}</td>
                        <td className="px-4 py-2">
                          <span className={`text-xs px-2 py-1 rounded ${
                            a.severity === 'critical' ? 'bg-sentinel-critical/20 text-sentinel-critical' :
                            a.severity === 'high' ? 'bg-sentinel-high/20 text-sentinel-high' :
                            a.severity === 'medium' ? 'bg-sentinel-medium/20 text-sentinel-medium' :
                            'bg-sentinel-low/20 text-sentinel-low'
                          }`}>{a.severity.toUpperCase()}</span>
                        </td>
                        <td className="px-4 py-2">{a.confidence}%</td>
                        <td className="px-4 py-2 text-xs text-sentinel-text-secondary truncate max-w-[100px]">{a.source_file}</td>
                        <td className="px-4 py-2 text-xs text-sentinel-text-secondary">{new Date(a.timestamp).toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {results.events.length > 0 && (
            <div className="bg-sentinel-card border border-sentinel-border rounded-xl overflow-hidden">
              <div className="p-4 border-b border-sentinel-border"><h3 className="text-sm font-semibold text-sentinel-text-secondary">Parsed Events ({results.events.length})</h3></div>
              <div className="overflow-x-auto max-h-96">
                <table className="w-full text-sm">
                  <thead><tr className="text-left text-sentinel-text-secondary border-b border-sentinel-border">
                    <th className="px-4 py-2 font-medium">Line</th>
                    <th className="px-4 py-2 font-medium">Time</th>
                    <th className="px-4 py-2 font-medium">Type</th>
                    <th className="px-4 py-2 font-medium">Severity</th>
                    <th className="px-4 py-2 font-medium">Message</th>
                  </tr></thead>
                  <tbody>
                    {results.events.slice(0, 50).map((e, i) => (
                      <tr key={i} className="border-b border-sentinel-border hover:bg-sentinel-border/30">
                        <td className="px-4 py-2 text-xs text-sentinel-text-secondary">{e.source_line}</td>
                        <td className="px-4 py-2 text-xs text-sentinel-text-secondary">{new Date(e.timestamp).toLocaleTimeString()}</td>
                        <td className="px-4 py-2 text-xs font-mono">{e.event_type}</td>
                        <td className="px-4 py-2">
                          <span className={`text-xs px-2 py-1 rounded ${
                            e.severity === 'critical' ? 'bg-sentinel-critical/20 text-sentinel-critical' :
                            e.severity === 'high' ? 'bg-sentinel-high/20 text-sentinel-high' :
                            e.severity === 'medium' ? 'bg-sentinel-medium/20 text-sentinel-medium' :
                            'bg-sentinel-low/20 text-sentinel-low'
                          }`}>{e.severity}</span>
                        </td>
                        <td className="px-4 py-2 text-xs max-w-xs truncate">{e.message}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}